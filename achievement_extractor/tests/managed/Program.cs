using System;
using System.IO;
using System.Diagnostics;
using System.Linq;
using System.Text.Json;
using Mono.Cecil;
using Mono.Cecil.Cil;

public static class Fixtures
{
    static MethodDefinition Method(TypeDefinition type,string name,TypeReference result,TypeReference argument=null)
    {
        var m=new MethodDefinition(name,MethodAttributes.Public|MethodAttributes.Static,result);
        if(argument!=null)m.Parameters.Add(new ParameterDefinition(argument));type.Methods.Add(m);return m;
    }
    public static int Main(string[] args)
    {
        string root=Path.Combine(Path.GetTempPath(),"achievement-scanner-"+Guid.NewGuid());Directory.CreateDirectory(root);
        try
        {
            using var module=ModuleDefinition.CreateModule("OwnAchievementFixture",ModuleKind.Dll);
            var api=new TypeDefinition("Steamworks","SteamUserStats",TypeAttributes.Public,module.TypeSystem.Object);module.Types.Add(api);
            var set=Method(api,"SetAchievement",module.TypeSystem.Boolean,module.TypeSystem.String);
            set.Body.Instructions.Add(Instruction.Create(OpCodes.Ldc_I4_1));set.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
            var reset=Method(api,"ResetAchievement",module.TypeSystem.Boolean,module.TypeSystem.String);
            reset.Body.Instructions.Add(Instruction.Create(OpCodes.Ldc_I4_1));reset.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
            var type=new TypeDefinition("","OwnGame",TypeAttributes.Public,module.TypeSystem.Object);module.Types.Add(type);
            var mapper=Method(type,"OwnNames",module.TypeSystem.String,module.TypeSystem.Int32);
            var branch=Instruction.Create(OpCodes.Ldstr,"MAP_A");
            mapper.Body.Instructions.Add(Instruction.Create(OpCodes.Ldarg_0));mapper.Body.Instructions.Add(Instruction.Create(OpCodes.Brfalse,branch));
            mapper.Body.Instructions.Add(Instruction.Create(OpCodes.Ldstr,"MAP_B"));mapper.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));mapper.Body.Instructions.Add(branch);mapper.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
            var start=Method(type,"OwnEvents",module.TypeSystem.Void,module.TypeSystem.String);var code=start.Body.Instructions;
            code.Add(Instruction.Create(OpCodes.Ldstr,"DIRECT"));code.Add(Instruction.Create(OpCodes.Call,set));code.Add(Instruction.Create(OpCodes.Pop));
            code.Add(Instruction.Create(OpCodes.Ldc_I4_0));code.Add(Instruction.Create(OpCodes.Call,mapper));code.Add(Instruction.Create(OpCodes.Call,set));code.Add(Instruction.Create(OpCodes.Pop));
            code.Add(Instruction.Create(OpCodes.Ldstr,"NOT_AN_UNLOCK"));code.Add(Instruction.Create(OpCodes.Call,reset));code.Add(Instruction.Create(OpCodes.Pop));
            code.Add(Instruction.Create(OpCodes.Ldarg_0));code.Add(Instruction.Create(OpCodes.Call,set));code.Add(Instruction.Create(OpCodes.Pop));code.Add(Instruction.Create(OpCodes.Ret));
            string path=Path.Combine(root,"OwnFixture.dll");module.Write(path);
            var info=new ProcessStartInfo(Path.GetFullPath(args[0])){RedirectStandardOutput=true,RedirectStandardError=true,UseShellExecute=false,CreateNoWindow=true};info.ArgumentList.Add(path);
            using var process=Process.Start(info);string data=process.StandardOutput.ReadToEnd();process.WaitForExit();if(process.ExitCode!=0)throw new Exception(process.StandardError.ReadToEnd());
            using var document=JsonDocument.Parse(data);var result=document.RootElement;
            string[] ids=result.GetProperty("rows").EnumerateArray().Select(x=>x.GetProperty("id").GetString()).OrderBy(x=>x).ToArray();
            if(!ids.SequenceEqual(new[]{"DIRECT","MAP_A","MAP_B"})||result.GetProperty("unresolved_calls").GetInt32()!=1)throw new Exception(data);
            Console.WriteLine("Managed scanner: direct IDs + return map recovered; reset excluded; dynamic call reported; no target execution.");return 0;
        }
        finally{Directory.Delete(root,true);}
    }
}
