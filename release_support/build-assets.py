from pathlib import Path
import subprocess
R=Path(__file__).resolve().parents[1];v=R/'port_studio/vendor/forwarder';out=R/'build/port-studio/tools/make-app-assets.exe';out.parent.mkdir(parents=True,exist_ok=True)
subprocess.run([str(R/'tools/zig-python/ziglang/zig.exe'),'c++','-std=c++20','-O2','-Wno-everything','-I'+str(v/'src'),'-I'+str(v),str(v/'tools/make-app-assets.cpp'),str(v/'src/fwd/image.cpp'),'-o',str(out)],check=True)
