// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;

namespace ProsperoAchievements
{
    // No Unity, Steam, network or platform API dependencies. Same DLL for each game.
    public static class Bridge
    {
        private static readonly object Gate = new object();
        private static Transport transport;

        // True means the PS5 route owns this request, even on a transport error.
        // Never fall back into an unavailable Steam library after accepting a context.
        public static bool TryUnlock(string sourceId)
        {
            lock (Gate)
            {
                try
                {
                    if (transport == null)
                        transport = Transport.Load(Path.Combine(Path.GetDirectoryName(typeof(Bridge).Assembly.Location),
                            "ProsperoAchievements.config.tsv"), @"C:\ProsperoAchievements");
                    bool accepted;
                    return transport.Record(sourceId, out accepted);
                }
                catch { return false; } // Missing/invalid config: original desktop path.
            }
        }
    }

    internal sealed class Transport
    {
        private readonly string game, root;
        private readonly Dictionary<string, string> ids;
        private readonly HashSet<string> sent = new HashSet<string>(StringComparer.Ordinal);
        private readonly object gate = new object();
        private static readonly UTF8Encoding Utf8 = new UTF8Encoding(false, true);

        private Transport(string gameId, string folder, Dictionary<string,string> mapping)
        { game = gameId; root = folder; ids = mapping; }

        internal static Transport Load(string path, string folder)
        {
            if (new FileInfo(path).Length > 131072) throw new InvalidDataException("Config too large");
            string[] lines = File.ReadAllLines(path, Utf8);
            if (lines.Length < 2 || lines.Length > 257) throw new InvalidDataException("Config rows");
            string[] header = lines[0].Split('\t');
            if (header.Length != 2 || header[0] != "PA_MANAGED_CONFIG_V1" ||
                !Regex.IsMatch(header[1], @"\A[a-z0-9][a-z0-9._-]{0,31}\z") || header[1].Contains(".."))
                throw new InvalidDataException("Config identity");
            var mapping = new Dictionary<string,string>(StringComparer.Ordinal);
            var canonical = new HashSet<string>(StringComparer.Ordinal);
            for (int i=1; i<lines.Length; ++i)
            {
                string[] fields = lines[i].Split('\t');
                if (fields.Length != 3 || fields[0] != "MAP" ||
                    !Regex.IsMatch(fields[2], @"\A[A-Za-z0-9][A-Za-z0-9._-]{0,63}\z") || fields[2].Contains(".."))
                    throw new InvalidDataException("Config mapping");
                string source = Utf8.GetString(Convert.FromBase64String(fields[1]));
                if (source.Length == 0 || Utf8.GetByteCount(source) > 256 || !canonical.Add(fields[2]))
                    throw new InvalidDataException("Config duplicate/empty");
                foreach (char ch in source) if (Char.IsControl(ch)) throw new InvalidDataException("Config controls");
                mapping.Add(source, fields[2]);
            }
            return new Transport(header[1], folder, mapping);
        }

        internal bool Record(string source, out bool accepted)
        {
            lock (gate)
            {
                accepted = false;
                string user;
                try
                {
                    string contextPath = Path.Combine(root, game + "-context-v1.txt");
                    if (new FileInfo(contextPath).Length > 256) return false;
                    string context = File.ReadAllText(contextPath, Utf8);
                    var match = Regex.Match(context, "\\APA_FILE_CONTEXT_V1\\t" + Regex.Escape(game) + "\\t([0-9a-f]{8})\\n\\z");
                    if (!match.Success) return false;
                    user = match.Groups[1].Value;
                }
                catch { return false; }
                // Everything below is owned by a validated local game/user context.
                try
                {
                    string id;
                    if (source == null || !ids.TryGetValue(source, out id)) return true;
                    string key = user + ":" + id;
                    if (sent.Contains(key)) { accepted = true; return true; }
                    string path = Path.Combine(root, game + "-" + user + ".tsv");
                    string header = "PA_FILE_BRIDGE_V1\t" + game + "\t" + user + "\n";
                    using (var file = new FileStream(path, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.Read))
                    {
                        if (file.Length == 0)
                        { byte[] start = Utf8.GetBytes(header); file.Write(start,0,start.Length); }
                        else
                        {
                            byte[] start = Utf8.GetBytes(header), actual = new byte[start.Length];
                            if (file.Read(actual,0,actual.Length) != actual.Length || Utf8.GetString(actual) != header)
                                return true;
                        }
                        file.Seek(0,SeekOrigin.End);
                        // Isolate an interrupted tail from the next complete native-reader record.
                        byte[] record = Utf8.GetBytes("\nPA_FILE_UNLOCK_V1\t" + game + "\t" + user + "\t" + id + "\n");
                        file.Write(record,0,record.Length); file.Flush(true);
                    }
                    sent.Add(key); accepted = true;
                }
                catch { /* Native bridge/outbox does the HTTP work. Never throw into gameplay. */ }
                return true;
            }
        }
    }
}
