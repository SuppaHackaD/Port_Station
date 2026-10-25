"""Real codec round trips, not just an output extension/header check."""
import array
import copy
import json
import math
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import wave
from port_station.audio import FFMPEG,ENCODER,transcode,validate_options,apply_metadata
from port_station.assets import validate_at9,prepare_presentation
from port_station.builder import Builder
from port_station.project import ProjectError,default_project,read_project,WORKSPACE

@unittest.skipUnless(FFMPEG.is_file(), "Optional FFmpeg: run release_support/install-ffmpeg.py for audio integration tests")
class AudioTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='studio-audio-test-');self.root=Path(self.temp.name)
        self.source=self.root/'ação 测试.wav';self.builder=Builder(log=lambda s:None)
        with wave.open(str(self.source),'wb')as f:
            f.setparams((2,2,44100,0,'NONE','not compressed'))
            f.writeframes(b''.join(struct.pack('<hh',int(14000*math.sin(2*math.pi*440*i/44100)),int(14000*math.sin(2*math.pi*660*i/44100)))for i in range(44100*2)))

    def tearDown(self):self.temp.cleanup()

    def convert(self,source=None,name='output.at9',**kwargs):
        path=self.root/name;report=transcode(source or self.source,path,self.builder.run,lambda s:None,**kwargs)
        validate_at9(path.read_bytes());return path,report

    def test_wav_resample_trim_stereo_loudness_and_independent_decode(self):
        original=self.source.read_bytes();path,report=self.convert(start=.25,duration=1)
        self.assertEqual(self.source.read_bytes(),original);self.assertEqual(report['samples'],48000)
        self.assertEqual(report['channels'],2);self.assertAlmostEqual(report['final_lufs'],-28,delta=.1)
        decoded=self.root/'decoded.f64';subprocess.run([str(FFMPEG),'-v','error','-y','-i',str(path),'-f','f64le','-c:a','pcm_f64le',str(decoded)],check=True,capture_output=True)
        samples=array.array('d',decoded.read_bytes());self.assertTrue(all(math.isfinite(x)for x in samples));self.assertLess(max(abs(x)for x in samples),.8)
        for channel,frequency in [(samples[::2],440),(samples[1::2],660)]:
            chunk=channel[2000:40000];n=len(chunk);power=sum(x*x for x in chunk)
            real=sum(x*math.cos(2*math.pi*frequency*i/48000)for i,x in enumerate(chunk));imag=sum(x*math.sin(2*math.pi*frequency*i/48000)for i,x in enumerate(chunk))
            self.assertGreater(2*(real*real+imag*imag)/n/power,.98)
        data=path.read_bytes();pos=data.index(b'smpl');self.assertEqual(struct.unpack_from('<I',data,pos+8+28)[0],1)
        self.assertEqual(struct.unpack_from('<I',data,pos+8+44)[0],256)
        self.assertEqual(struct.unpack_from('<I',data,pos+8+48)[0],48000+255)

    def test_mp3_ogg_flac_m4a_inputs(self):
        for suffix,codec in [('mp3','libmp3lame'),('ogg','libvorbis'),('flac','flac'),('m4a','aac')]:
            with self.subTest(suffix=suffix):
                source=self.root/('input.'+suffix)
                subprocess.run([str(FFMPEG),'-v','error','-y','-i',str(self.source),'-c:a',codec,str(source)],check=True,capture_output=True)
                path,report=self.convert(source,'result-'+suffix+'.at9',duration=.5)
                self.assertEqual(report['mode'],'transcoded');self.assertEqual(report['samples'],24000)
                subprocess.run([str(FFMPEG),'-v','error','-i',str(path),'-f','null','-'],check=True,capture_output=True)

    def test_existing_at9_is_unchanged_and_clip_not_applied(self):
        path,report=self.convert(duration=.5);copy_path,copied=self.convert(path,'copy.at9',start=10,duration=1)
        self.assertEqual(path.read_bytes(),copy_path.read_bytes());self.assertFalse(copied['clip_options_applied']);self.assertIsNone(copied['final_lufs'])

    def test_output_and_source_never_overwritten(self):
        target=self.root/'existing.at9';target.write_bytes(b'preserve')
        with self.assertRaises(ProjectError):transcode(self.source,target,self.builder.run,duration=.5)
        self.assertEqual(target.read_bytes(),b'preserve')

    def test_invalid_offsets_and_duration_rejected(self):
        for start,duration in [(-1,15),(0,0),(0,88),(float('nan'),15),(0,float('inf')),(False,15)]:
            with self.subTest(start=start,duration=duration),self.assertRaises(ProjectError):validate_options(start,duration)

    def test_start_beyond_eof_leaves_no_output(self):
        with self.assertRaises(ProjectError):self.convert(start=100,duration=1)
        self.assertFalse((self.root/'output.at9').exists())

    def test_silence_is_valid_json_and_decodes(self):
        silent=self.root/'silent.wav'
        with wave.open(str(silent),'wb')as f:f.setparams((1,2,32000,0,'NONE','not compressed'));f.writeframes(bytes(32000*2))
        path,report=self.convert(silent,duration=.5);self.assertIsNone(report['source_lufs']);self.assertIsNone(report['final_lufs'])
        json.dumps(report,allow_nan=False)
        subprocess.run([str(FFMPEG),'-v','error','-i',str(path),'-f','null','-'],check=True,capture_output=True)

    def test_full_presentation_records_conversion_and_metadata(self):
        p=read_project(WORKSPACE/'port_station/examples/tcoaal.ps5port.json');p.update(sound=str(self.source),audio_start=.2,audio_duration=.5)
        report=prepare_presentation(p,WORKSPACE/'port_station/examples',self.root/'presentation',self.builder.run,lambda s:None)
        self.assertTrue((self.root/'presentation/snd0.at9').is_file());self.assertTrue((self.root/'audio-report.json').is_file())
        param={};apply_metadata(param,report);self.assertEqual(param['pubtools']['loudnessSnd0'],format(report['final_lufs'],'.2f'))
        empty={};apply_metadata(empty,None);self.assertEqual(empty,{})

    def test_legacy_project_audio_defaults(self):
        p=read_project(WORKSPACE/'port_station/examples/tcoaal.ps5port.json');self.assertEqual(p['audio_start'],0);self.assertEqual(p['audio_duration'],15)

    def test_maximum_duration_stays_within_console_limit(self):
        source=self.root/'long.wav'
        with wave.open(str(source),'wb')as f:f.setparams((1,2,48000,0,'NONE','not compressed'));f.writeframes(bytes(48000*88*2))
        path,report=self.convert(source,duration=87.3)
        self.assertEqual(report['samples'],4190400);self.assertLessEqual(path.stat().st_size,2097152)
        subprocess.run([str(FFMPEG),'-v','error','-i',str(path),'-f','null','-'],check=True,capture_output=True)

if __name__=='__main__':unittest.main()
