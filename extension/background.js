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
            // testLocalStore();
            // testGetLocalStore('logs4');
            console.log(`download_stored_object - message:\n${JSON.stringify(message, null, ' ')}`);
            console.log(`message.storage_key: ${message.storage_key}`);
            browser.storage.local.get(message.storage_key)
                .then((storedObject) => {
                    console.log(`storedObject keys: ${Object.keys(storedObject)}`);
                    let meditationLogs = storedObject[message.storage_key];
                    console.log(`background retrieved storage: ${message.storage_key}`);
                    console.log(`meditationLogs.length: ${meditationLogs.length}`)
                    console.log(`typeof meditationLogs: ${typeof meditationLogs}`)
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

function testLocalStore() {
    let logs = ['one', 'two'];
    browser.storage.local.set({'example2': logs}).then(() => {
        browser.storage.local.get('example2').then(logs =>
        console.log(`got example2: ${JSON.stringify(logs)}`),
            reportError)
    }, reportError)
        .catch(reportError)
}

function testGetLocalStore(keyName) {
    browser.storage.local.get(keyName).then(logs2 =>
    console.log(`${keyName}: ${JSON.stringify(logs2)}`),
        reportError).catch(reportError)
    console.log('done test get store');
}

/*
let logs = ['one', 'two']
result = browser.storage.local.set({'logs': logs})
browser.storage.local.get('logs').then(logs => {console.log(JSON.stringify(logs))}).catch(error => console.log(`error: ${error}`))

 */