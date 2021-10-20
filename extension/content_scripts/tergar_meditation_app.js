/**
 * This script pulls the meditation logs from local storage used by Redux.
 * It stores them and passes a message to the background script to download.
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
     * Calls client scraper function, stores resulting object into local storage with key,
     * then notifies background script to download it to filename in the user's
     * download directory.
     * Right now download options are to download automatically - ie no prompt for the user
     * and to overwrite an existing file with the same name.
     *
     * @param scrapeFunction - called with no params, must return object that works with local
     * storage (jsonifiable)
     * @param storageKey - string for storage key - alphanumeric + underscore are ok
     * @param filename - filename that will be downloaded to in the user's download directory
     * @returns {Promise<void>}
     */
    function scrapeStoreAndNotifyBackend(scrapeFunction, storageKey, filename) {
        console.log("scrapeStoreAndNotifyBackend() ..");
        let objectToStore = scrapeFunction();
        return browser.storage.local.set({[storageKey]: objectToStore})
            .then(() => {
                console.log(`stored data with key: ${storageKey} and filename: ${filename}`);
                browser.runtime.sendMessage({
                    "target": "background",
                    "command": "download_stored_object",
                    "storage_key": storageKey,
                    "filename": filename,
                });
            })
            .catch(reportError);
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
            // testLocalStore('logs4');
            // browser.runtime.sendMessage({
            //     "target": "background",
            //     "command": "download_stored_object",
            //     "storage_key": storageKey
            // });
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

    function testLocalStore(keyName) {
        let logs = ['one', 'two'];
        let storeObj = {};
        storeObj[keyName] = logs;
        browser.storage.local.set(storeObj).then(() => {
            browser.storage.local.get(keyName).then(logs2 =>
                    console.log(`got ${keyName}: ${JSON.stringify(logs2)}`),
                reportError)
        }, reportError)
            .catch(reportError)
    }


})();
