// Nerd Font loader for JupyterLab terminal
// Load font via BOTH FontFace JS API (for Canvas) and CSS @font-face (for OffscreenCanvas).
// The test page proved FontFace API works for canvas rendering.
(function() {
    // Load via FontFace API (guaranteed to work for Canvas fillText)
    var regular = new FontFace("FiraCode Nerd Font", "url(/static/lab/fonts/FiraCodeNerdFontMono-Regular.woff2)");
    var bold = new FontFace("FiraCode Nerd Font", "url(/static/lab/fonts/FiraCodeNerdFontMono-Bold.woff2)", {weight: "700"});
    Promise.all([regular.load(), bold.load()]).then(function(fonts) {
        fonts.forEach(function(f) { document.fonts.add(f); });
    });
    // Also trigger CSS @font-face download
    document.fonts.load('14px "FiraCode Nerd Font"');
})();
