// Own synthetic assemblies only. No Unity or commercial game files.
using System;
using System.IO;
using Mono.Cecil;
using Mono.Cecil.Cil;

public static class VerifierTests
{
    static MethodDefinition Method(TypeDefinition type, string name, TypeReference result, bool argument = false)
    {
        var method = new MethodDefinition(name, MethodAttributes.Public | MethodAttributes.Static, result);
        if (argument) method.Parameters.Add(new ParameterDefinition(type.Module.TypeSystem.Int32));
        type.Methods.Add(method);
        return method;
    }
    public static int Main()
    {
        string folder = Path.Combine(Path.GetTempPath(), "port-station-cil-" + Guid.NewGuid());
        Directory.CreateDirectory(folder);
        try
        {
            using var bridge = ModuleDefinition.CreateModule("BreathPS5Bridge", ModuleKind.Dll);
            var helper = new TypeDefinition("", "BreathPS5Bridge", TypeAttributes.Public, bridge.TypeSystem.Object);
            bridge.Types.Add(helper);
            var route = Method(helper, "TryUnlock", bridge.TypeSystem.Boolean, true);
            route.Body.Instructions.Add(Instruction.Create(OpCodes.Ldc_I4_1));
            route.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
            var announce = Method(helper, "SessionStart", bridge.TypeSystem.Void);
            announce.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
            string bridgePath = Path.Combine(folder, "BreathPS5Bridge.dll");
            bridge.Write(bridgePath);
            using var module = ModuleDefinition.CreateModule("OwnFixture", ModuleKind.Dll);
            var type = new TypeDefinition("", "SteamAchievments", TypeAttributes.Public, module.TypeSystem.Object);
            module.Types.Add(type);
            var start = Method(type, "Start", module.TypeSystem.Void);
            start.Body.Instructions.Add(Instruction.Create(OpCodes.Call, module.ImportReference(announce)));
            start.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
            var unlock = Method(type, "Conquista", module.TypeSystem.Void, true);
            var original = Instruction.Create(OpCodes.Ret);
            unlock.Body.Instructions.Add(Instruction.Create(OpCodes.Ldarg_0));
            unlock.Body.Instructions.Add(Instruction.Create(OpCodes.Call, module.ImportReference(route)));
            var branch = Instruction.Create(OpCodes.Brfalse, original);
            unlock.Body.Instructions.Add(branch);
            unlock.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
            unlock.Body.Instructions.Add(original);
            string assemblyPath = Path.Combine(folder, "OwnFixture.dll");
            void Check(bool accepted)
            {
                module.Write(assemblyPath);
                int result = PatchBreathAchievements.Main(new[] { "--verify", assemblyPath, bridgePath });
                if ((result == 0) != accepted) throw new Exception("Unexpected verification result: " + result);
            }
            Check(true);
            branch.Operand = unlock.Body.Instructions[3];
            Check(false); // corrupt fallback branch
            branch.Operand = original;
            start.Body.Instructions[0].OpCode = OpCodes.Nop;
            start.Body.Instructions[0].Operand = null;
            Check(false); // filename exists, session bridge absent
            unlock.Body.Instructions.Clear();
            unlock.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
            Check(false); // filename exists, unlock bridge absent
            Console.WriteLine("4 managed verifier cases passed using owned fixtures.");
            return 0;
        }
        finally { Directory.Delete(folder, true); }
    }
}
