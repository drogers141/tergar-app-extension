/**
 * Listen for clicks on the popup, and send the appropriate message to
 * the content script in the active tab.
 */
function listenForClicks() {
  document.addEventListener("click", (e) => {
    if (e.target.classList.contains("button")) {
      browser.tabs.query({active: true, currentWindow: true})
          .then(tabs => {
              browser.tabs.sendMessage(
                  tabs[0].id,
                  {command: "store_meditation_logs"}
              ).catch(reportError)
          })
          .catch(reportError);
    }
  });
}

function reportError(error) {
  console.error(`Popup could not send message to content script: ${error}`);
}

listenForClicks();
