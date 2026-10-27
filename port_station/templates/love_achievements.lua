-- SPDX-License-Identifier: MIT
-- Mirrors real game award calls to the owned, per-user file bridge.
return function(config)
  local api=love and love.platformAPI
  local function callable(f) return type(f)=='function' or type(f)=='cdata' end
  if type(api)~='table' or not callable(api.SetAchievement) then
    print('PA_LOVE unavailable: platform award API missing'); return nil
  end
  if api.__prospero_achievements_v1 then return api.__prospero_achievements_v1 end
  local ok,ffi=pcall(require,'ffi')
  if not ok then print('PA_LOVE unavailable: ffi missing'); return nil end
  ffi.cdef[[int pa_event_ready_v1(const char*,const char*);
            int pa_event_unlock_v1(const char*,const char*,const char*);]]
  local loaded,library=pcall(ffi.load,'paevents.dll')
  if not loaded then print('PA_LOVE unavailable: '..tostring(library)); return nil end
  local folder=config.folder or 'C:/ProsperoAchievements'
  local queue,waiting,sent={},{},{}
  local ready,next_at=false,0
  local client={}
  local function clock()
    return love.timer and love.timer.getTime and love.timer.getTime() or os.clock()
  end
  function client.flush()
    if not ready then
      local rc=tonumber(library.pa_event_ready_v1(folder,config.gameId))
      if rc~=0 then return rc end
      ready=true; print('PA_LOVE event bridge ready')
    end
    local i=1
    while i<=#queue do
      local id=queue[i]
      local rc=tonumber(library.pa_event_unlock_v1(folder,config.gameId,id))
      if rc~=0 then return rc end
      sent[id]=true;waiting[id]=nil;table.remove(queue,i)
      print('PA_LOVE recorded '..id)
    end
    return 0
  end
  function client.unlock(source)
    local id=type(source)=='string' and config.aliases[source]
    if not id or sent[id] or waiting[id] then return false end
    waiting[id]=true;queue[#queue+1]=id;pcall(client.flush);return true
  end
  local function pack(...) return {n=select('#',...),...} end
  local award=api.SetAchievement
  api.SetAchievement=function(...)
    local result=pack(award(...))
    pcall(client.unlock,select(1,...))
    return unpack(result,1,result.n)
  end
  local function pulse(force)
    local now=clock()
    if force or now>=next_at then next_at=now+0.25;pcall(client.flush) end
  end
  if callable(api.updateAPI) then
    local update=api.updateAPI
    api.updateAPI=function(...)
      local result=pack(update(...));pulse(false);return unpack(result,1,result.n)
    end
  end
  if callable(api.release) then
    local release=api.release
    api.release=function(...) pulse(true);return release(...) end
  end
  api.__prospero_achievements_v1=client
  pcall(client.flush)
  return client
end
