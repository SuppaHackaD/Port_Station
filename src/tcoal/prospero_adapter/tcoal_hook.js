/* Wrap only the game's observed award entrypoint; preserve its return/exception. */
(function () {
    'use strict';
    var publisher = null, installed = false, attempts = 0;
    var ids = __TCOAL_IDS__;
    function install() {
        attempts++;
        try {
            if (!publisher) publisher = ProsperoFileBridge.create({gameId: 'tcoal', contextFile: 'C:/ProsperoAchievements/tcoal-context-v1.txt', achievementIds: ids});
            if (!installed && typeof Steam !== 'undefined' && typeof Steam.awardAchievement === 'function') {
                var original = Steam.awardAchievement;
                Steam.awardAchievement = function (id) {
                    // Honor the game's own test-mode suppression; never infer from a loaded save.
                    try { if (typeof Utils === 'undefined' || !Utils.isOptionValid('test')) publisher.unlock(id); } catch (e) {}
                    return original.apply(this, arguments);
                };
                installed = true; publisher.markReady();
                window.TCOALProspero = {version: '0.1.0', userId: publisher.userId, installed: true};
            }
            if (installed) { publisher.markReady(); publisher.flush(); }
        } catch (e) { /* Keep the game playable if transport/storage is unavailable. */ }
        if (installed || attempts < 1200) setTimeout(install, installed ? 1000 : 50);
    }
    install();
}());
