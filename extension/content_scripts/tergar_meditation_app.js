/**
 * This content script pulls the meditation logs from local storage used by
 * Redux Persist.
 *
 * It stores them in the extension's local storage and passes a message to the
 * background script to download.
 */

(function () {
    /**
     * Check and set a global guard variable.
     * If this content script is injected into the same page again,
     * it will do nothing next time.
     */
    if (window.hasRun) {
        return;
    }
    window.hasRun = true;
    window.URL = window.URL || window.webkitURL;

    function reportError(error) {
        console.error(`tergar_meditation_app.js error: ${error}`);
    }

    /**
     * Message passing interface
     *
     * command: "store_meditation_logs"
     * key for stored meditation logs: "meditation_logs"
     */
    browser.runtime.onMessage.addListener((message) => {
        if (message.command === "store_meditation_logs") {
            console.log('Content script received store_meditation_logs message.');
            const storageKey = "meditation_logs";
            storeMeditationLogs(storageKey).then(
                browser.runtime.sendMessage({
                    "target": "background",
                    "command": "download_stored_object",
                    "storage_key": storageKey
                }), reportError
            ).catch(reportError)

        } else {
            reportError(`Unknown message command: ${message.command}`);
        }
    });

    /**
     * Store regular and mala meditation logs in browser.local storage
     *
     * @param key - key name for stored object
     * @return promise - result of StorageArea.set()
     */
    async function storeMeditationLogs(key) {
        console.log(`Storing meditation logs with key name: ${key}`)
        let meditationLogs = JSON.parse(window.localStorage.getItem('reduxPersist:dataMeditation'));
        let malaMedLogs = JSON.parse(window.localStorage.getItem('reduxPersist:dataMalaMeditation'));
        console.log(`regular meditation logs: ${meditationLogs.length}`)
        console.log(`mala meditation logs: ${malaMedLogs.length}`);
        meditationLogs = meditationLogs.concat(malaMedLogs);
        let storeObj = {};
        storeObj[key] = meditationLogs;
        return browser.storage.local.set(storeObj);
    }
})();
