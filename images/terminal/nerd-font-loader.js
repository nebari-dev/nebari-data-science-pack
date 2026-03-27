// Nerd Font loader for JupyterLab terminal
// On first visit, the font downloads from the network. xterm.js initializes
// before the font is ready and renders boxes. The simplest reliable fix:
// reload the page once after the font loads (on first visit only).
// Subsequent visits use the cached font and don't need a reload.
(function() {
    document.fonts.load('14px "FiraCode Nerd Font"').then(function() {
        if (!sessionStorage.getItem("nf-loaded")) {
            sessionStorage.setItem("nf-loaded", "1");
            location.reload();
        }
    });
})();
