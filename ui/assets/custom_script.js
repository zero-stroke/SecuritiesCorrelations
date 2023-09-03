document.addEventListener('DOMContentLoaded', function(){
    document.getElementById(SECURITIES_INPUT_ID).onkeypress = function(e){
        if (e.keyCode === 13) {
            document.getElementById(LOAD_PLOT_BUTTON_ID).click();
        }
    };
});
