// Nerd Font loader for JupyterLab terminal
// Force-load the font and patch xterm.js terminals when they appear.
(function() {
    var nfFont = "'FiraCode Nerd Font', 'Fira Code', monospace";

    // Force font download (CSS @font-face is lazy)
    document.fonts.load('14px "FiraCode Nerd Font"');

    // Watch for terminals and patch their font
    new MutationObserver(function() {
        document.querySelectorAll(".xterm").forEach(function(el) {
            if (el.dataset.nfPatched) return;
            el.dataset.nfPatched = "1";
            document.fonts.load('14px "FiraCode Nerd Font"').then(function() {
                setTimeout(function() {
                    // Find the xterm Terminal instance via the textarea
                    var ta = el.querySelector(".xterm-helper-textarea");
                    if (ta) {
                        var keys = Object.keys(ta);
                        for (var i = 0; i < keys.length; i++) {
                            try {
                                var obj = ta[keys[i]];
                                if (obj && obj._core && obj._core.options) {
                                    obj._core.options.fontFamily = nfFont;
                                    obj._core.options.fontSize = 14;
                                    obj._core.options.lineHeight = 1.2;
                                    break;
                                }
                                if (obj && obj.options && obj.options.fontFamily) {
                                    obj.options.fontFamily = nfFont;
                                    obj.options.fontSize = 14;
                                    obj.options.lineHeight = 1.2;
                                    break;
                                }
                            } catch(e) {}
                        }
                    }
                    window.dispatchEvent(new Event("resize"));
                }, 500);
            });
        });
    }).observe(document.documentElement, {childList: true, subtree: true});
})();
