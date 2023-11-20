// // Attempt to add key listening for Ctrl + Enter
//
// if (!window.dash_clientside) {
//     window.dash_clientside = {};
// }
//
// window.dash_clientside.clientside = {
//     detect_ctrl_enter: function(n_blur, current_val) {
//         var hiddenInput = document.getElementById('hidden-input');
//         var textarea = document.getElementById('textarea-input');
//
//         textarea.addEventListener('keydown', function(event) {
//             if (event.ctrlKey && event.key === 'Enter') {
//                 hiddenInput.value = parseInt(hiddenInput.value) + 1;
//             }
//         });
//
//         return hiddenInput.value;
//     }
// };
