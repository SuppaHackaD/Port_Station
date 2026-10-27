// SPDX-License-Identifier: GPL-3.0-or-later
using Mono.Cecil;
using Mono.Cecil.Cil;
using System.Security.Cryptography;
using System.Text.Json;

// Offline only: reads assembly/dependency metadata; never executes game code.
// Accept a deliberately narrow achievement-only wrapper, not arbitrary game methods.
static class Program
{
    static IEnumerable<TypeDefinition> Types(IEnumerable<TypeDefinition> source)
    { foreach(var t in source) { yield return t; foreach(var c in Types(t.NestedTypes)) yield return c; } }

    static bool Call(Instruction i, string type, string name, string returns, params string[] args) =>
        i.OpCode == OpCodes.Call && i.Operand is MethodReference m && !m.HasThis &&
        m.DeclaringType.FullName == type && m.Name == name && m.ReturnType.FullName == returns &&
        m.Parameters.Select(p=>p.ParameterType.FullName).SequenceEqual(args);

    static bool Supported(MethodDefinition m)
    {
        if (!m.IsStatic || !m.HasBody || m.HasGenericParameters || m.ReturnType.FullName!="System.Void" ||
            m.Parameters.Count!=1 || m.Parameters[0].ParameterType.FullName!="System.String" ||
            m.Body.ExceptionHandlers.Count!=0 || m.Body.Variables.Count!=1 ||
            m.Body.Variables[0].VariableType.FullName!="System.Boolean") return false;
        var a=m.Body.Instructions.Where(i=>i.OpCode!=OpCodes.Nop).ToArray();
        // if(Initialized) { GetAchievement(id,out exists); if(!exists) { SetAchievement(id); StoreStats(); } }
        return a.Length==14 && a[0].Operand is MethodReference ready && ready.Name=="get_Initialized" &&
            ready.DeclaringType.Name=="SteamManager" && !ready.HasThis && ready.Parameters.Count==0 &&
            ready.ReturnType.FullName=="System.Boolean" && a[0].OpCode==OpCodes.Call &&
            (a[1].OpCode==OpCodes.Brfalse || a[1].OpCode==OpCodes.Brfalse_S) && a[1].Operand==a[13] &&
            a[2].OpCode==OpCodes.Ldarg_0 && (a[3].OpCode==OpCodes.Ldloca_S || a[3].OpCode==OpCodes.Ldloca) &&
            a[3].Operand==m.Body.Variables[0] &&
            Call(a[4],"Steamworks.SteamUserStats","GetAchievement","System.Boolean","System.String","System.Boolean&") &&
            a[5].OpCode==OpCodes.Pop && a[6].OpCode==OpCodes.Ldloc_0 &&
            (a[7].OpCode==OpCodes.Brtrue || a[7].OpCode==OpCodes.Brtrue_S) && a[7].Operand==a[13] &&
            a[8].OpCode==OpCodes.Ldarg_0 && Call(a[9],"Steamworks.SteamUserStats","SetAchievement","System.Boolean","System.String") &&
            a[10].OpCode==OpCodes.Pop && Call(a[11],"Steamworks.SteamUserStats","StoreStats","System.Boolean") &&
            a[12].OpCode==OpCodes.Pop && a[13].OpCode==OpCodes.Ret;
    }

    static int Main(string[] args)
    {
        try
        {
            if(args.Length!=1 && args.Length!=4) throw new Exception("Usage: integrator ASSEMBLY [BRIDGE_DLL OUTPUT EXPECTED_SOURCE_SHA256]");
            string sha=Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(args[0])));
            using var resolver=new DefaultAssemblyResolver();
            resolver.AddSearchDirectory(Path.GetDirectoryName(Path.GetFullPath(args[0]))!);
            using var module=ModuleDefinition.ReadModule(args[0],new ReaderParameters {
                AssemblyResolver=resolver, ReadingMode=ReadingMode.Deferred, ReadSymbols=false });
            var matches=Types(module.Types).SelectMany(t=>t.Methods).Where(Supported).ToArray();
            var unhandled=Types(module.Types).SelectMany(t=>t.Methods).Where(m=>m.HasBody && !matches.Contains(m) &&
                m.Body.Instructions.Any(i=>i.Operand is MethodReference call && call.DeclaringType.FullName=="Steamworks.SteamUserStats" && call.Name=="SetAchievement"))
                .Select(m=>m.FullName).ToArray();
            if(args.Length==1)
            {
                Console.WriteLine(JsonSerializer.Serialize(new {sha256=sha, methods=matches.Select(m=>new {name=m.FullName,token=m.MetadataToken.ToInt32()}),
                    supported=matches.Length>0,unhandled_achievement_methods=unhandled,scope="achievement-only-string-wrapper-v1"})); return 0;
            }
            if(sha!=args[3]) throw new Exception("Source hash changed since inspection");
            if(matches.Length==0) throw new Exception("No supported achievement-only wrapper. Manual adapter required; no file changed.");
            if(unhandled.Length>0) throw new Exception("Other achievement methods need a manual adapter; automatic integration would be partial. No file changed.");
            if(module.Assembly.Name.HasPublicKey) throw new Exception("Strong-named assembly not supported");
            if(File.Exists(args[2]) || Path.GetFullPath(args[2])==Path.GetFullPath(args[0])) throw new Exception("Output must be a new file");
            using var bridge=ModuleDefinition.ReadModule(args[1]);
            var api=bridge.GetType("ProsperoAchievements.Bridge").Methods.Single(m=>m.Name=="TryUnlock");
            foreach(var method in matches)
            {
                var il=method.Body.GetILProcessor(); var first=method.Body.Instructions[0];
                // New prefix executes only on method entry. Original control flow remains intact.
                il.InsertBefore(first,Instruction.Create(OpCodes.Ldarg_0));
                il.InsertBefore(first,Instruction.Create(OpCodes.Call,module.ImportReference(api)));
                il.InsertBefore(first,Instruction.Create(OpCodes.Brfalse,first));
                il.InsertBefore(first,Instruction.Create(OpCodes.Ret));
                method.Body.MaxStackSize=Math.Max(2,method.Body.MaxStackSize);
            }
            string temporary=args[2]+".incomplete";
            if(File.Exists(temporary)) throw new Exception("Incomplete output already exists; choose a new output");
            try
            {
                module.Write(temporary);
                using(var verify=ModuleDefinition.ReadModule(temporary))
                {
                    foreach(var original in matches)
                    {
                        var method=Types(verify.Types).SelectMany(t=>t.Methods).Single(m=>m.FullName==original.FullName);
                        if(method.Body.Instructions[1].Operand is not MethodReference mr ||
                           mr.DeclaringType.FullName!="ProsperoAchievements.Bridge" || mr.Name!="TryUnlock")
                            throw new Exception("Written bridge reference did not verify");
                    }
                }
                File.Move(temporary,args[2]);
            }
            finally { if(File.Exists(temporary)) File.Delete(temporary); }
            Console.WriteLine(JsonSerializer.Serialize(new {source_sha256=sha, methods=matches.Select(m=>m.FullName),
                output_sha256=Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(args[2])))}));
            return 0;
        }
        catch(Exception e) { Console.Error.WriteLine(e.Message); return 1; }
    }
}
