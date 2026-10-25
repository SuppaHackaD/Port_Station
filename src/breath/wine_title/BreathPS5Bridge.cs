// Achievement transport for the private PS5 copy. No Unity or Steam API dependency.
using System;
using System.Globalization;
using System.IO;
using System.Text;

public static class BreathPS5Bridge
{
#if BREATH_BRIDGE_TEST
    private static readonly string Folder = Environment.GetEnvironmentVariable("BREATH_BRIDGE_TEST_ROOT");
#else
    private const string Folder = @"C:\BreathPS5";
#endif
    private static readonly object Gate = new object();
    private static uint emitted;
    private static bool announced;

    private static bool Context(out string user)
    {
        user = null;
        string path = Path.Combine(Folder, "context-v1.txt");
        if (!File.Exists(path)) return false;
        string text = File.ReadAllText(path);
        const string head = "BREATH_CONTEXT_V1\t";
        uint number;
        if (text.Length != head.Length + 9 || !text.StartsWith(head, StringComparison.Ordinal) ||
            text[text.Length - 1] != '\n' ||
            !UInt32.TryParse(text.Substring(head.Length, 8), NumberStyles.HexNumber,
                            CultureInfo.InvariantCulture, out number) || number > Int32.MaxValue ||
            text != head + number.ToString("x8", CultureInfo.InvariantCulture) + "\n")
            throw new IOException("Invalid PS5 achievement user context");
        user = number.ToString("x8", CultureInfo.InvariantCulture);
        return true;
    }

    private static void Append(string user, string line)
    {
        string path = Path.Combine(Folder, "events-" + user + ".tsv");
        using (FileStream file = new FileStream(path, FileMode.Append, FileAccess.Write, FileShare.ReadWrite))
        {
            if (file.Length > 4 * 1024 * 1024) throw new IOException("Achievement queue limit reached");
            byte[] bytes = new UTF8Encoding(false).GetBytes(line);
            file.Write(bytes, 0, bytes.Length);
            file.Flush(true);
        }
    }

    private static void Announce(string user)
    {
        if (announced) return;
        Append(user, "BREATH_BRIDGE_V1\t" + user + "\n");
        announced = true;
    }

    public static void SessionStart()
    {
        lock (Gate)
        {
            try { string user; if (Context(out user)) Announce(user); }
            catch (Exception error) { Console.Error.WriteLine("BREATH ACH bridge initialization: " + error.Message); }
        }
    }

    // true means this PS5 build handled the achievement; the desktop fallback
    // retains the original Steam branch when no PS5 context exists.
    public static bool TryUnlock(int id)
    {
        lock (Gate)
        {
            try
            {
                string user;
                if (!Context(out user)) return false;
                if (id < 0 || id >= 11) return true;
                Announce(user);
                uint bit = 1u << id;
                if ((emitted & bit) != 0) return true;
                Append(user, "BREATH_UNLOCK_V1\t" + user + "\t" + id.ToString(CultureInfo.InvariantCulture) + "\n");
                emitted |= bit;
            }
            catch (Exception error)
            {
                // An achievement transport failure must not interrupt gameplay
                // or try to start a desktop service on the console.
                Console.Error.WriteLine("BREATH ACH bridge write: " + error.Message);
            }
            return true;
        }
    }
}
