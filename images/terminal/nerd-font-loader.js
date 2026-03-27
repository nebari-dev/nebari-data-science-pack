// Nerd Font loader for JupyterLab terminal
// Forces font download, then triggers xterm.js to re-measure by writing
// terminal settings via the JupyterLab REST API (which fires the settings
// changed signal → setOption("fontFamily") → xterm re-measures).
(function() {
    var FONT = "'FiraCode Nerd Font', 'Fira Code', monospace";
    var PLUGIN = "@jupyterlab/terminal-extension:plugin";

    // Force font download (CSS @font-face is lazy)
    document.fonts.load('14px "FiraCode Nerd Font"');

    // Watch for terminals and trigger font re-measurement
    new MutationObserver(function() {
        document.querySelectorAll(".xterm").forEach(function(el) {
            if (el.dataset.nfPatched) return;
            el.dataset.nfPatched = "1";

            // Wait for font to load, then force xterm to re-measure by
            // writing settings via the REST API. This triggers:
            // ISettingRegistry.changed → v(e) → b() → setOption("fontFamily")
            // which is the ONLY way to make xterm.js re-measure font dimensions.
            document.fonts.load('14px "FiraCode Nerd Font"').then(function() {
                setTimeout(function() {
                    // Get XSRF token from cookie
                    var xsrf = "";
                    document.cookie.split(";").forEach(function(c) {
                        c = c.trim();
                        if (c.startsWith("_xsrf=")) xsrf = c.substring(6);
                    });

                    // PUT terminal settings to trigger the changed signal
                    var settings = {
                        fontFamily: FONT,
                        fontSize: 14,
                        lineHeight: 1.2
                    };
                    fetch("/lab/api/settings/" + PLUGIN, {
                        method: "PUT",
                        headers: {
                            "Content-Type": "application/json",
                            "X-XSRFToken": xsrf
                        },
                        body: JSON.stringify({ raw: JSON.stringify(settings) })
                    }).then(function() {
                        // Double-trigger resize for good measure
                        setTimeout(function() {
                            window.dispatchEvent(new Event("resize"));
                        }, 200);
                    });
                }, 500);
            });
        });
    }).observe(document.documentElement, {childList: true, subtree: true});
})();
