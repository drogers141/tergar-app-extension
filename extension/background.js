/**
 * This background script is only responsible for downloading the meditation
 * logs.
 */

browser.runtime.onMessage.addListener(handleMessages);

function reportError(error) {
    console.error(`background.js error: ${error}`);
}

/**
 * Message passing interface - target - "background"
 * command: "download_stored_object"
 * @param message
 */
function handleMessages(message) {
    if (message.target === "background") {
        if (message.command === "download_stored_object") {
            console.log(`download_stored_object - message:\n${JSON.stringify(message, null, ' ')}`);
            browser.storage.local.get(message.storage_key)
                .then((storedObject) => {
                    let meditationLogs = storedObject[message.storage_key];
                    console.log(`background retrieved storage: ${message.storage_key}`);
                    const blob = new Blob([JSON.stringify(meditationLogs)]);
                    const url = URL.createObjectURL(blob);
                    const timestampString = moment().format().replace(/:/g, '.');
                    console.log("timestamp: ", timestampString);
                    const filename = `tergar-meditation-logs-${timestampString}.json`;
                    browser.downloads.download({
                        url: url,
                        filename: filename,
                        conflictAction: "overwrite",
                        saveAs: false
                    });
                    console.log(`background downloaded storage to file: ${filename}`);
                }, reportError)
                .catch(reportError);
        } else {
            reportError(`Unknown message command: ${message.command}`)
        }
    }
}
