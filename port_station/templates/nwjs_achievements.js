/* Game events only. A catalog entry is never proof that its condition was met. */
(function () {
    'use strict';
    var config = __CONFIG__, records = {}, publisher = null, tries = 0;
    function canonical(id) {
        if (typeof id !== 'string') return null;
        if (Object.prototype.hasOwnProperty.call(config.aliases, id)) return config.aliases[id];
        return config.ids.indexOf(id) >= 0 ? id : null;
    }
    function wrap(object, key, label) {
        if (!object || typeof object[key] !== 'function') return false;
        if (records[label] && records[label].object === object && records[label].wrapper === object[key]) return true;
        var original = object[key];
        var wrapper = function () {
            try {
                var id = canonical(arguments[0]);
                var test = typeof Utils !== 'undefined' && typeof Utils.isOptionValid === 'function' && Utils.isOptionValid('test');
                if (id && !test) publisher.unlock(id);
            } catch (e) { /* Keep the game's original return/exception behavior. */ }
            return original.apply(this, arguments);
        };
        object[key] = wrapper;
        if (object[key] !== wrapper) return false;
        records[label] = {object: object, wrapper: wrapper};
        return true;
    }
    function install() {
        tries++;
        var installed = false;
        try {
            if (!publisher) publisher = ProsperoFileBridge.create({gameId: config.gameId, contextFile: 'C:/ProsperoAchievements/' + config.gameId + '-context-v1.txt', achievementIds: config.ids});
            if (typeof Steam !== 'undefined') {
                installed = wrap(Steam, 'awardAchievement', 'game');
                installed = wrap(Steam.API, 'activateAchievement', 'api') || installed;
            }
            if (installed) { publisher.markReady(); publisher.flush(); }
        } catch (e) {}
        if (installed || tries < 1200) setTimeout(install, installed ? 1000 : 50);
    }
    install();
}());
