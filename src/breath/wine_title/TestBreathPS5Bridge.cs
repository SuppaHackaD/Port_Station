using System;
public static class TestBreathPS5Bridge
{
    public static int Main(string[] args)
    {
        BreathPS5Bridge.SessionStart();
        foreach(string arg in args) Console.WriteLine("route="+arg+":"+BreathPS5Bridge.TryUnlock(Int32.Parse(arg)));
        return 0;
    }
}
