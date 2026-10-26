// Own fixtures only. Never loads a commercial game's assembly.
using System.Reflection;
using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Security.Cryptography;
using Mono.Cecil;
using Mono.Cecil.Cil;

static class Tests
{
 static int checks;
 static void Check(bool value,string message) { if(!value) throw new Exception(message);checks++; }
 static string Run(string exe,params string[] args)
 {
  var info=new ProcessStartInfo(exe) {RedirectStandardOutput=true,RedirectStandardError=true,UseShellExecute=false};
  foreach(var arg in args) info.ArgumentList.Add(arg);
  using var p=Process.Start(info)!;var text=p.StandardOutput.ReadToEnd();var error=p.StandardError.ReadToEnd();p.WaitForExit();
  if(p.ExitCode!=0) throw new Exception(error);return text;
 }
 static void Fixture(string path,bool extraCondition=false)
 {
  using var m=ModuleDefinition.CreateModule("OwnFixture",ModuleKind.Dll);
  var manager=new TypeDefinition("","SteamManager",Mono.Cecil.TypeAttributes.Public,m.TypeSystem.Object);m.Types.Add(manager);
  var ready=new MethodDefinition("get_Initialized",Mono.Cecil.MethodAttributes.Public|Mono.Cecil.MethodAttributes.Static,m.TypeSystem.Boolean);
  ready.Body.Instructions.Add(Instruction.Create(OpCodes.Ldc_I4_0));ready.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));manager.Methods.Add(ready);
  var steam=new TypeDefinition("Steamworks","SteamUserStats",Mono.Cecil.TypeAttributes.Public,m.TypeSystem.Object);m.Types.Add(steam);
  MethodDefinition Api(string name,params TypeReference[] args)
  {
   var api=new MethodDefinition(name,Mono.Cecil.MethodAttributes.Public|Mono.Cecil.MethodAttributes.Static,m.TypeSystem.Boolean);
   foreach(var arg in args) api.Parameters.Add(new ParameterDefinition(arg));
   api.Body.Instructions.Add(Instruction.Create(OpCodes.Ldc_I4_1));api.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));steam.Methods.Add(api);return api;
  }
  var get=Api("GetAchievement",m.TypeSystem.String,new ByReferenceType(m.TypeSystem.Boolean));
  var set=Api("SetAchievement",m.TypeSystem.String);var store=Api("StoreStats");
  var type=new TypeDefinition("Own","Achievements",Mono.Cecil.TypeAttributes.Public,m.TypeSystem.Object);m.Types.Add(type);
  var unlock=new MethodDefinition("Award",Mono.Cecil.MethodAttributes.Public|Mono.Cecil.MethodAttributes.Static,m.TypeSystem.Void);
  unlock.Parameters.Add(new ParameterDefinition(m.TypeSystem.String));unlock.Body.InitLocals=true;unlock.Body.Variables.Add(new VariableDefinition(m.TypeSystem.Boolean));type.Methods.Add(unlock);
  var il=unlock.Body.GetILProcessor();var ret=Instruction.Create(OpCodes.Ret);
  if(extraCondition) { il.Append(Instruction.Create(OpCodes.Ldc_I4_0));il.Append(Instruction.Create(OpCodes.Brfalse,ret)); }
  foreach(var instruction in new[]{Instruction.Create(OpCodes.Call,ready),Instruction.Create(OpCodes.Brfalse_S,ret),
    Instruction.Create(OpCodes.Ldarg_0),Instruction.Create(OpCodes.Ldloca_S,unlock.Body.Variables[0]),Instruction.Create(OpCodes.Call,get),
    Instruction.Create(OpCodes.Pop),Instruction.Create(OpCodes.Ldloc_0),Instruction.Create(OpCodes.Brtrue_S,ret),
    Instruction.Create(OpCodes.Ldarg_0),Instruction.Create(OpCodes.Call,set),Instruction.Create(OpCodes.Pop),Instruction.Create(OpCodes.Call,store),Instruction.Create(OpCodes.Pop),ret}) il.Append(instruction);
  m.Write(path);
 }
 static int Main(string[] args)
 {
  if(args.Length!=2)throw new Exception("Tests INTEGRATOR_EXE BRIDGE_DLL");
  string dir=Path.Combine(Path.GetTempPath(),"pa-managed-own-tests-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(dir);
  try
  {
   var dll=Assembly.LoadFrom(Path.GetFullPath(args[1]));
   var transport=dll.GetType("ProsperoAchievements.Transport",true)!;
   var load=transport.GetMethod("Load",BindingFlags.Static|BindingFlags.NonPublic)!;
   var record=transport.GetMethod("Record",BindingFlags.Instance|BindingFlags.NonPublic)!;
   string config=Path.Combine(dir,"config.tsv");
   File.WriteAllText(config,"PA_MANAGED_CONFIG_V1\town.test\nMAP\t"+Convert.ToBase64String(Encoding.UTF8.GetBytes("Source ç"))+"\tCANONICAL\n",new UTF8Encoding(false));
   var instance=load.Invoke(null,new object[]{config,dir})!;
   bool Emit(string source,out bool accepted)
   { object[] a={source,false};var handled=(bool)record.Invoke(instance,a)!;accepted=(bool)a[1];return handled; }
   Check(!Emit("Source ç",out _),"Missing context must retain desktop route");
   string context=Path.Combine(dir,"own.test-context-v1.txt");
   File.WriteAllText(context,"PA_FILE_CONTEXT_V1\twrong\t1758d77d\n");Check(!Emit("Source ç",out _),"Cross-game context rejected");
   File.WriteAllText(context,"PA_FILE_CONTEXT_V1\town.test\t11111111\n");
   Check(Emit("UNKNOWN",out var accepted)&&!accepted,"Unknown IDs never emitted");
   Check(Emit("Source ç",out accepted)&&accepted,"Mapped genuine request accepted");
   Check(Emit("Source ç",out accepted)&&accepted,"Replay accepted");
   string events=Path.Combine(dir,"own.test-11111111.tsv");
   Check(File.ReadAllLines(events).Count(x=>x.StartsWith("PA_FILE_UNLOCK_V1"))==1,"One record per session/user/ID");
   Check(File.ReadAllText(events)=="PA_FILE_BRIDGE_V1\town.test\t11111111\n\nPA_FILE_UNLOCK_V1\town.test\t11111111\tCANONICAL\n","Native protocol exact");
   File.WriteAllText(context,"PA_FILE_CONTEXT_V1\town.test\t22222222\n");Check(Emit("Source ç",out accepted)&&accepted,"User switch accepted independently");
   File.WriteAllText(context,"PA_FILE_CONTEXT_V1\town.test\t33333333\n");File.WriteAllText(Path.Combine(dir,"own.test-33333333.tsv"),"WRONG\n");
   Check(Emit("Source ç",out accepted)&&!accepted,"Corrupt stream handled without Steam fallback");
   string original=Path.Combine(dir,"original.dll"),patched=Path.Combine(dir,"patched.dll"),unsupported=Path.Combine(dir,"complex.dll");
   Fixture(original);Fixture(unsupported,true);
   using(var report=JsonDocument.Parse(Run(args[0],original)))Check(report.RootElement.GetProperty("supported").GetBoolean(),"Safe wrapper detected");
   using(var report=JsonDocument.Parse(Run(args[0],unsupported)))Check(!report.RootElement.GetProperty("supported").GetBoolean(),"Gameplay conditions reject automatic wrapping");
   string sha=Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(original)));
   Run(args[0],original,args[1],patched,sha);
   Check(Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(original)))==sha,"Original unchanged");
   using(var m=ModuleDefinition.ReadModule(patched))
   {
    var body=m.GetType("Own.Achievements").Methods.Single().Body.Instructions;
    Check(body.Count==18 && body[1].Operand is MethodReference mr && mr.FullName.Contains("ProsperoAchievements.Bridge::TryUnlock"),"Exact entry routing");
    Check(body[2].Operand==body[4] && body[3].OpCode==OpCodes.Ret,"Desktop fallback preserves original entry");
    Check(body[5].Operand==body[17] && body[11].Operand==body[17],"Original branch targets preserved");
   }
   // Execute only our generated fixture, using our transport and local test identity.
   dll.GetType("ProsperoAchievements.Bridge")!.GetField("transport",BindingFlags.Static|BindingFlags.NonPublic)!.SetValue(null,instance);
   File.WriteAllText(context,"PA_FILE_CONTEXT_V1\town.test\t44444444\n");
   var fixture=Assembly.Load(File.ReadAllBytes(patched));fixture.GetType("Own.Achievements")!.GetMethod("Award")!.Invoke(null,new object[]{"Source ç"});
   Check(File.Exists(Path.Combine(dir,"own.test-44444444.tsv")),"Patched fixture reaches compiled net40 bridge");
   Console.WriteLine($"Managed bridge/integrator: {checks} checks passed (own fixtures only)");return 0;
  }
  finally { Directory.Delete(dir,true); }
 }
}
