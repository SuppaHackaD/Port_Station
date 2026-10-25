/* Original game/API awards only; transport errors never change original behavior. */
(function () {
    'use strict';
    var ids = __TCOAL_IDS__, allowed = Object.create(null), aliases = Object.create(null), publisher = null, attempts = 0, records = {}, logCount = 0;
    ids.forEach(function (id) {
        var key = id.toLowerCase();
        if (aliases[key] && aliases[key] !== id) throw new Error('Ambiguous TCOAL achievement alias');
        allowed[id] = true; aliases[key] = id;
    });
    var state = {version: '0.3.0', installed: false, primaryInstalled: false, apiInstalled: false, requests: 0, publishedRequests: 0, unknown: 0, testSkipped: 0, errors: 0};
    window.TCOALProspero = state;
    function log(event, data) {
        if (!publisher || logCount >= 256) return;
        try {
            require('fs').appendFileSync('C:/ProsperoAchievements/tcoal-bridge-v3-' + publisher.userId + '.jsonl', JSON.stringify({at: Date.now(), user: publisher.userId, event: event, data: data}) + '\n', 'utf8');
            logCount++;
        } catch (e) {}
    }
    function capture(id, layer) {
        state.requests++;
        var canonical = typeof id === 'string' ? (allowed[id] ? id : aliases[id.toLowerCase()]) : null;
        var known = !!canonical, test = false, sent = false, error = null;
        try {
            test = typeof Utils !== 'undefined' && typeof Utils.isOptionValid === 'function' && Utils.isOptionValid('test');
            if (test) state.testSkipped++;
            else if (known) { sent = publisher.unlock(canonical); if (sent) state.publishedRequests++; }
            else state.unknown++;
        } catch (e) { state.errors++; error = String(e); }
        log('award.request', {layer: layer, id: typeof id === 'string' ? id.slice(0,128) : null, type: typeof id, canonicalId: canonical || null, known: known, testMode: test, published: !!sent, error: error || publisher.lastError || null});
    }
    function ensure(object, key, layer) {
        if (!object || typeof object[key] !== 'function') return false;
        if (records[layer] && records[layer].object === object && records[layer].wrapper === object[key]) return true;
        var original = object[key], replaced = !!records[layer];
        var wrapper = function () {
            if (layer === 'choice') {
                if (typeof arguments[0] === 'string' && /\((?:label|lines)\)\s*\[/.test(arguments[0])) log('choice.unresolved', {text: arguments[0].slice(0,300)});
            } else capture(arguments[0], layer);
            return original.apply(this, arguments);
        };
        try {
            object[key] = wrapper;
            if (object[key] !== wrapper) return false;
            records[layer] = {object: object, wrapper: wrapper};
            log('hook.ready', {layer: layer, replaced: replaced}); return true;
        } catch (e) { log('hook.failed', {layer: layer, error: String(e)}); return false; }
    }
    function install() {
        attempts++;
        try {
            if (!publisher) {
                publisher = ProsperoFileBridge.create({gameId: 'tcoal', contextFile: 'C:/ProsperoAchievements/tcoal-context-v1.txt', achievementIds: ids});
                state.userId = publisher.userId; log('transport.ready', {version: state.version});
            }
            if (typeof Steam !== 'undefined') {
                state.primaryInstalled = ensure(Steam, 'awardAchievement', 'game');
                state.apiInstalled = ensure(Steam.API, 'activateAchievement', 'api');
            }
            if (typeof Window_ChoiceList !== 'undefined') ensure(Window_ChoiceList.prototype, 'addCommand', 'choice');
            state.installed = state.primaryInstalled || state.apiInstalled;
            if (state.installed) { publisher.markReady(); publisher.flush(); }
        } catch (e) { state.errors++; log('transport.error', {error: String(e)}); }
        if (state.installed || attempts < 1200) setTimeout(install, state.installed ? 1000 : 50);
    }
    install();
}());
