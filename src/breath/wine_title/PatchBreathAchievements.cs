using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using Mono.Cecil;
using Mono.Cecil.Cil;

public static class PatchBreathAchievements
{
    private static bool Calls(Instruction instruction, MethodDefinition target)
    {
        var reference = instruction.Operand as MethodReference;
        var scope = reference == null ? null : reference.DeclaringType.Scope as AssemblyNameReference;
        return instruction.OpCode == OpCodes.Call && reference != null &&
            reference.FullName == target.FullName && scope != null &&
            scope.Name == target.Module.Assembly.Name.Name;
    }

    private static void VerifyPrepared(string assemblyPath, string bridgePath)
    {
        using var module = ModuleDefinition.ReadModule(assemblyPath);
        using var bridge = ModuleDefinition.ReadModule(bridgePath);
        var type = module.GetType("SteamAchievments");
        var bridgeType = bridge.GetType("BreathPS5Bridge");
        if (type == null || bridgeType == null) throw new InvalidDataException("Breath bridge types not found");
        MethodDefinition unlock = null, start = null, route = null, announce = null;
        foreach (var method in type.Methods)
        { if (method.Name == "Conquista") unlock = method; if (method.Name == "Start") start = method; }
        foreach (var method in bridgeType.Methods)
        { if (method.Name == "TryUnlock") route = method; if (method.Name == "SessionStart") announce = method; }
        if (unlock == null || start == null || route == null || announce == null ||
            !unlock.IsStatic || unlock.Parameters.Count != 1 || !route.IsStatic ||
            route.Parameters.Count != 1 || route.Parameters[0].ParameterType.FullName != "System.Int32" ||
            route.ReturnType.FullName != "System.Boolean" || !announce.IsStatic ||
            announce.Parameters.Count != 0 || announce.ReturnType.FullName != "System.Void" ||
            !start.HasBody || !unlock.HasBody)
            throw new InvalidDataException("Unexpected prepared Breath signature");
        var init = start.Body.Instructions;
        var instructions = unlock.Body.Instructions;
        if (init.Count < 2 || !Calls(init[0], announce) || instructions.Count < 5 ||
            instructions[0].OpCode != OpCodes.Ldarg_0 || !Calls(instructions[1], route) ||
            instructions[2].OpCode != OpCodes.Brfalse || instructions[2].Operand != instructions[4] ||
            instructions[3].OpCode != OpCodes.Ret)
            throw new InvalidDataException("Breath achievement calls are not connected to the PS5 bridge. Use the supported original copy or prepare it again.");
        Console.WriteLine("Verified Breath bridge: session announcement and unlock route before Steam access.");
    }

    private static IEnumerable<TypeDefinition> Types(IEnumerable<TypeDefinition> list)
    {
        foreach (TypeDefinition type in list)
        {
            yield return type;
            foreach (TypeDefinition nested in Types(type.NestedTypes)) yield return nested;
        }
    }

    private static string Shape(MethodDefinition method)
    {
        if (!method.HasBody) return "no-body";
        var body = method.Body;
        var text = new System.Text.StringBuilder();
        foreach (VariableDefinition local in body.Variables) text.Append("local:" + local.VariableType.FullName + ";");
        foreach (Instruction instruction in body.Instructions)
        {
            text.Append(instruction.OpCode.Name + ":");
            object operand = instruction.Operand;
            if (operand is Instruction) text.Append(body.Instructions.IndexOf((Instruction)operand));
            else if (operand is Instruction[])
                foreach (Instruction target in (Instruction[])operand) text.Append(body.Instructions.IndexOf(target) + ",");
            else text.Append(operand == null ? "" : operand.ToString());
            text.Append(";");
        }
        foreach (ExceptionHandler handler in body.ExceptionHandlers)
            text.Append("eh:" + handler.HandlerType + ":" + handler.CatchType + ":" +
                body.Instructions.IndexOf(handler.TryStart) + ":" + body.Instructions.IndexOf(handler.TryEnd) + ":" +
                body.Instructions.IndexOf(handler.HandlerStart) + ":" + body.Instructions.IndexOf(handler.HandlerEnd) + ";");
        return text.ToString();
    }

    public static int Main(string[] args)
    {
        if (args.Length == 3 && args[0] == "--verify")
        {
            try { VerifyPrepared(args[1], args[2]); return 0; }
            catch (Exception error)
            { Console.Error.WriteLine("Breath preparation check failed: " + error.Message); return 2; }
        }
        if (args.Length != 3) throw new ArgumentException("original assembly, bridge assembly, new output");
        byte[] input = File.ReadAllBytes(args[0]);
        string hash = BitConverter.ToString(SHA256.Create().ComputeHash(input)).Replace("-", "").ToLowerInvariant();
        if (hash != "b98be2ab162e9f7f2ff4029b0bf8221db075df052d5782b96c73424c6ee95f18")
            throw new InvalidDataException("Unrecognized Breath assembly");
        if (File.Exists(args[2])) throw new IOException("Output must be new");
        var module = ModuleDefinition.ReadModule(new MemoryStream(input));
        var bridge = ModuleDefinition.ReadModule(args[1]);
        TypeDefinition type = module.GetType("SteamAchievments"), bridgeType = bridge.GetType("BreathPS5Bridge");
        MethodDefinition unlock = null, start = null, route = null, announce = null;
        var before = new Dictionary<string, string>();
        foreach (TypeDefinition item in Types(module.Types))
            foreach (MethodDefinition method in item.Methods) before.Add(method.FullName, Shape(method));
        foreach (MethodDefinition method in type.Methods)
        { if (method.Name == "Conquista") unlock = method; if (method.Name == "Start") start = method; }
        foreach (MethodDefinition method in bridgeType.Methods)
        { if (method.Name == "TryUnlock") route = method; if (method.Name == "SessionStart") announce = method; }
        if (unlock == null || start == null || route == null || announce == null ||
            unlock.Parameters.Count != 1 || !unlock.IsStatic || !route.IsStatic)
            throw new InvalidDataException("Unexpected bridge target signature");
        Instruction original = unlock.Body.Instructions[0];
        var il = unlock.Body.GetILProcessor();
        il.InsertBefore(original, il.Create(OpCodes.Ldarg_0));
        il.InsertBefore(original, il.Create(OpCodes.Call, module.ImportReference(route)));
        il.InsertBefore(original, il.Create(OpCodes.Brfalse, original));
        il.InsertBefore(original, il.Create(OpCodes.Ret));
        start.Body.GetILProcessor().InsertBefore(start.Body.Instructions[0],
            Instruction.Create(OpCodes.Call, module.ImportReference(announce)));
        module.Mvid = new Guid("39420630-e10f-4c7e-8432-b149651ded82");
        module.Write(args[2]);
        var written = ModuleDefinition.ReadModule(args[2]);
        int changed = 0, total = 0;
        foreach (TypeDefinition item in Types(written.Types)) foreach (MethodDefinition method in item.Methods)
        {
            total++;
            if (before[method.FullName] == Shape(method)) continue;
            if (method.FullName != unlock.FullName && method.FullName != start.FullName)
                throw new InvalidDataException("Unexpected method change: " + method.FullName);
            changed++;
            Console.WriteLine("changed=" + method.FullName);
        }
        if (changed != 2 || total != before.Count) throw new InvalidDataException("Method inventory changed");
        VerifyPrepared(args[2], args[1]);
        Console.WriteLine("Verified " + total + " method bodies: only achievement Start and Conquista changed.");
        return 0;
    }
}
