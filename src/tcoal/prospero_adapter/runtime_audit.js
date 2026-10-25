/* Passive compatibility diagnostic. No unlocks, network calls or game-state writes. */
(function () {
    'use strict';
    var fs, file = 'C:/TCOAL-prospero-audit-v1.jsonl', count = 0, sourceBudget = 0;
    try { fs = require('fs'); } catch (e) { return; }
    function own(object, key) {
        try { var d = Object.getOwnPropertyDescriptor(object, key); return d && Object.prototype.hasOwnProperty.call(d, 'value') ? d.value : undefined; }
        catch (e) { return undefined; }
    }
    function keys(o) { try { return Object.getOwnPropertyNames(o).sort(); } catch (e) { return []; } }
    function source(f, limit) {
        if (sourceBudget <= 0) return '[source budget exhausted]';
        var s = Function.prototype.toString.call(f).slice(0, Math.min(limit, sourceBudget));
        sourceBudget -= s.length; return s;
    }
    function describe(o, sources) {
        var out = {type: typeof o, keys: keys(o).slice(0, 160)}, values = {};
        out.keys.forEach(function (key) {
            var v = own(o, key);
            if (typeof v === 'function' && sources && /achiev|steam|unlock|init|save|load|language|command|setup|boot|start/i.test(key)) {
                try { values[key] = {type: 'function', source: source(v, 12000)}; } catch (e) {}
            } else if (/achiev|steam|unlock|lang|version/i.test(key) && (typeof v === 'boolean' || typeof v === 'number' || typeof v === 'string' && v.length <= 160)) {
                values[key] = v;
            }
        });
        out.values = values; return out;
    }
    function method(target, name) {
        var f = own(target, name);
        if (typeof f !== 'function') return {available: false};
        try { return {available: true, source: source(f, 20000)}; }
        catch (e) { return {available: true, error: String(e)}; }
    }
    function sample() {
        sourceBudget = 96 * 1024;
        var result = {schema: 1, diagnostic: 'tcoal-prospero-readonly-v1', sample: ++count, at: Date.now()}, names = keys(window);
        result.candidates = names.filter(function (n) { return /achiev|greenworks|steam|tcoaal|coffin|language|globalmanager/i.test(n); });
        result.objects = {};
        result.candidates.slice(0, 32).forEach(function (n) { var o = own(window, n); if (o !== undefined) result.objects[n] = describe(o, true); });
        result.methods = {};
        if (typeof DataManager !== 'undefined') {
            result.data_manager = describe(DataManager, false);
            ['autoSave', 'loadDatabase', 'onLoad', 'setupNewGame', 'extractSaveContents'].forEach(function (n) { result.methods['DataManager.' + n] = method(DataManager, n); });
        }
        if (typeof ConfigManager !== 'undefined') result.config_manager = describe(ConfigManager, true);
        if (typeof Window_Options !== 'undefined') result.methods['Window_Options.addGeneralOptions'] = method(Window_Options.prototype, 'addGeneralOptions');
        if (typeof Game_Interpreter !== 'undefined') result.methods['Game_Interpreter.pluginCommand'] = method(Game_Interpreter.prototype, 'pluginCommand');
        if (typeof $gameSystem !== 'undefined' && $gameSystem) result.game_system = describe($gameSystem, false);
        try { result.scene = SceneManager._scene && SceneManager._scene.constructor.name; } catch (e) {}
        try { result.scripts = Array.prototype.map.call(document.scripts, function (s) { return s.src; }); } catch (e) {}
        try {
            result.modules = keys(require.cache).filter(function (p) { return /greenworks|steam|coffin|tcoaal|achiev/i.test(p); }).slice(0, 48);
            result.module_exports = {};
            result.modules.forEach(function (p) { var m = own(require.cache, p), x = m && own(m, 'exports'); if (x) result.module_exports[p] = describe(x, true); });
        } catch (e) { result.module_error = String(e); }
        // Bounded sampling: at most twelve records; no player save or config files opened.
        try { fs.appendFileSync(file, JSON.stringify(result) + '\n', 'utf8'); } catch (e) {}
        if (count < 12) setTimeout(sample, 5000);
    }
    setTimeout(sample, 3000);
}());
