/**
 * Listen for clicks on the buttons, and send the appropriate message to
 * the content script in the page.
 */
function listenForClicks() {
  document.addEventListener("click", (e) => {

    function handleClick() {
      browser.runtime.sendMessage({
        "target": "background",
        "command": "fetch_meditation_logs",
      });
      console.log("sent message to backend to fetch and store api");
      // // alert("Got click");
      // browser.tabs.sendMessage(tabs[0].id, {
      //   command: "scrape_and_store"
      //
      // console.log("sent scrape_and_store command");
    }

    // if (e.target.classList.contains("button")) {
    //   handleClick();
    // }

    if (e.target.classList.contains("button")) {
      browser.tabs.query({active: true, currentWindow: true})
          .then(handleClick)
          .catch(reportError);
    }
  });
}

function reportError(error) {
  console.error(`Could not send message: ${error}`);
}

/**
 * There was an error executing the script.
 * Display the popup's error message, and hide the normal UI.
 */
function reportExecuteScriptError(error) {
  document.querySelector("#popup-content").classList.add("hidden");
  document.querySelector("#error-content").classList.remove("hidden");
  console.error(`Failed to execute content script: ${error.message}`);
}

listenForClicks();
/**
 * ******** For Tergar Site **********
 */
// browser.tabs.executeScript({file: "/content_scripts/tergar_meditation_app.js"})
//     .then(listenForClicks)
//     .catch(reportExecuteScriptError);
