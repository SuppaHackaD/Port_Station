// Static metadata/CIL only. Does not resolve dependencies or execute target code.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mono.Cecil;
using Mono.Cecil.Cil;

public static class Program
{
    static IEnumerable<TypeDefinition> Types(IEnumerable<TypeDefinition> items)
    { foreach (var type in items) { yield return type; foreach(var child in Types(type.NestedTypes)) yield return child; } }
    static bool IsAchievementApi(MethodReference method)
    {
        return new[]{"SetAchievement","GetAchievement","UnlockAchievement","ActivateAchievement","AwardAchievement"}.Contains(method.Name) &&
            (method.DeclaringType.FullName.Contains("Steam") || method.DeclaringType.FullName.Contains("Achievement"));
    }
    static IEnumerable<string> ReturnedLiterals(MethodDefinition method)
    {
        if(!method.HasBody || method.ReturnType.FullName!="System.String") yield break;
        var code=method.Body.Instructions;
        for(int i=0;i+1<code.Count;i++)
            if(code[i].OpCode==OpCodes.Ldstr && code[i+1].OpCode==OpCodes.Ret) yield return (string)code[i].Operand;
    }
    public static int Main(string[] args)
    {
        var rows=new List<object>();var errors=new List<object>();var seen=new HashSet<string>();int unresolved=0;
        foreach(string path in args.Take(32))
        {
            try
            {
                using var module=ModuleDefinition.ReadModule(path,new ReaderParameters{ReadingMode=ReadingMode.Deferred,ReadSymbols=false});
                foreach(var type in Types(module.Types)) foreach(var method in type.Methods)
                {
                    if(!method.HasBody) continue;
                    var code=method.Body.Instructions;
                    for(int i=1;i<code.Count && rows.Count<4096;i++)
                    {
                        var call=code[i].Operand as MethodReference;
                        if((code[i].OpCode!=OpCodes.Call && code[i].OpCode!=OpCodes.Callvirt)||call==null||!IsAchievementApi(call))continue;
                        int p=call.Parameters.ToList().FindIndex(x=>x.ParameterType.FullName=="System.String");
                        // Only a last-argument string is directly established here.
                        if(p<0 || p!=call.Parameters.Count-1){unresolved++;continue;}
                        var previous=code[i-1];var values=new List<string>();string kind="managed-api-literal";
                        if(previous.OpCode==OpCodes.Ldstr)values.Add((string)previous.Operand);
                        else if(previous.OpCode==OpCodes.Call && previous.Operand is MethodDefinition mapper && mapper.Module==module)
                        {values.AddRange(ReturnedLiterals(mapper));kind="managed-return-map";}
                        if(values.Count==0)unresolved++;
                        foreach(string id in values)
                        {
                            if(id.Length==0||id.Length>256||id.Any(char.IsControl))continue;
                            string identity=path+"\0"+id;
                            if(seen.Add(identity))rows.Add(new{id,kind,path,method=method.FullName,token=method.MetadataToken.ToString(),il_offset=code[i].Offset});
                        }
                    }
                }
            }
            catch(Exception e){errors.Add(new{path,error=e.GetType().Name+": "+e.Message});}
        }
        Console.Write(JsonSerializer.Serialize(new{schema=1,rows,errors,unresolved_calls=unresolved,truncated=rows.Count>=4096||args.Length>32}));
        return 0;
    }
}
