/* File transport for Node/NW.js ports. Native adapter consumes the same user stream. */
(function (root) {
    'use strict';
    function create(options) {
        var fs = options.fs || require('fs'), game = options.gameId, allowed = Object.create(null);
        if (!/^[a-z0-9][a-z0-9._-]{0,63}$/.test(game) || game.indexOf('..') >= 0) throw new Error('invalid game id');
        options.achievementIds.forEach(function (id) { if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(id)) throw new Error('invalid achievement id'); allowed[id] = true; });
        var context = fs.readFileSync(options.contextFile, 'utf8'), match = /^PA_FILE_CONTEXT_V1\t([a-z0-9._-]+)\t([0-9a-f]{8})\n$/.exec(context);
        if (!match || match[1] !== game) throw new Error('missing or foreign user context');
        var user = match[2], directory = options.contextFile.replace(/[/\\][^/\\]+$/, '');
        var stream = directory + '/' + game + '-' + user + '.tsv', seen = Object.create(null), pending = Object.create(null), ready = false;
        var api = {userId: user, gameId: game, lastError: null};
        function append(line) {
            var fd, bytes = Buffer.from('\n' + line, 'utf8'), offset = 0;
            try {
                fd = fs.openSync(stream, 'a');
                while (offset < bytes.length) { var n = fs.writeSync(fd, bytes, offset, bytes.length - offset, null); if (n <= 0) throw new Error('short write'); offset += n; }
                fs.fsyncSync(fd); fs.closeSync(fd); fd = undefined; api.lastError = null; return true;
            } catch (e) { api.lastError = String(e); return false; }
            finally { if (fd !== undefined) try { fs.closeSync(fd); } catch (e) {} }
        }
        api.flush = function () {
            if (!ready) return false;
            var ok = true;
            Object.keys(pending).forEach(function (id) {
                if (append('PA_FILE_UNLOCK_V1\t' + game + '\t' + user + '\t' + id + '\n')) { seen[id] = true; delete pending[id]; }
                else ok = false;
            });
            return ok;
        };
        api.markReady = function () { if (!ready) ready = append('PA_FILE_BRIDGE_V1\t' + game + '\t' + user + '\n'); return ready; };
        api.unlock = function (id) {
            if (typeof id !== 'string' || !allowed[id]) return false;
            if (seen[id]) return true;
            pending[id] = true; if (!ready) api.markReady(); api.flush(); return !!seen[id];
        };
        return api;
    }
    var exported = {version: '0.1.0', create: create};
    if (typeof window === 'undefined' && typeof module !== 'undefined' && module.exports) module.exports = exported;
    root.ProsperoFileBridge = exported;
}(typeof window !== 'undefined' ? window : globalThis));
