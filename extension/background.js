
// ******* Use for tls security info
// async function logSubject(details) {
//     try {
//         let securityInfo = await browser.webRequest.getSecurityInfo(details.requestId, {});
//         console.log(details.url);
//         if (securityInfo.state === "secure" || securityInfo.state === "weak") {
//             console.log(securityInfo.certificates[0].subject);
//         }
//         var strProps = "securityInfo:\n";
//         for (var p in securityInfo) {
//             strProps += `${p}: ${securityInfo[p]}\n`;
//         }
//         console.log(strProps);
//     }
//     catch(error) {
//         console.error(error);
//     }
// }
//
// browser.webRequest.onHeadersReceived.addListener(logSubject,
//     {urls: ["*://app.tergar.org/*"]},
//     ["blocking"]
// );

const MEDITATION_API_FETCH_KEY = "meditation-log-api-fetch";

function storeAPIGetRequest(requestInfo) {
    let url = requestInfo.url;
    let headers = requestInfo.requestHeaders;
    var ua = "n/a", accept = "n/a", accept_lang = "n/a", auth = "n/a", refer = "n/a";
    for (var h of headers) {
        console.log(`header: ${h}`);
        if (h.name === "User-Agent") {
            console.log("got ua");
            ua = h.value;
        }
        if (h.name === "Accept") accept = h.value;
        if (h.name === "Accept-Language") accept_lang = h.value;
        if (h.name === "Authorization") auth = h.value;
        if (h.name === "Referer") refer = h.value;
    }
    let fetchBody = {
        "credentials": "include",
        "headers": {
            "User-Agent": ua,
            "Accept": accept,
            "Accept-Language": accept_lang,
            "Authorization": auth,
            "Cache-Control": "max-age=0"
        },
        "referrer": refer,
        "method": "GET",
        "mode": "cors"
    };
    browser.storage.local.set({
        [MEDITATION_API_FETCH_KEY]:
            {"url": url,
            "fetchBody": fetchBody}
    })
        .then(() => {
            console.log(`stored meditation log api - url: ${url}`);
        })
        .catch(reportError);
}

function logRequestWithHeaders(request) {
    logURL(request);
    for (var h of request.requestHeaders) {
        console.log(`header:\nname: ${h.name}\nvalue: ${h["value"]},\nbinaryValue: ${h["binaryValue"]}`);
    }
    if (request.url == "https://app.tergar.org/api/v2/meditation") {
        console.log("storing meditation api call");
        storeAPIGetRequest(request);
    }
}

browser.webRequest.onBeforeSendHeaders.addListener(
    logRequestWithHeaders,
    {urls: ["*://app.tergar.org/api/v2/*"]},
    ["blocking", "requestHeaders"]
);

function logURL(requestDetails) {
    let ts = moment().format();
    console.log(`${ts}: Loading ${requestDetails.url}`);
    // console.log(`requestDetails: ${JSON.parse( JSON.stringify(requestDetails))}`);
    var strProps = "requestDetails:\n";
    for (var p in requestDetails) {
        strProps += `${p}: ${requestDetails[p]}\n`;
    }
    console.log(strProps);

}
// browser.webRequest.onCompleted.addListener(
//     logURL,
//     {urls: ["*://app.tergar.org/*"]}
// );
// browser.webRequest.onBeforeRequest.addListener(
//     logURL,
//     {urls: ["*://app.tergar.org/*"]}
//     // {urls: ["<all_urls>"]}
// );

browser.runtime.onMessage.addListener(handleMessages);

function reportError(error) {
    console.error(`background.js error: ${error}`);
}

function checkStorage() {
    console.log(`checking storage: ${MEDITATION_API_FETCH_KEY}`);
    browser.storage.local.get(MEDITATION_API_FETCH_KEY)
        .then(function(apiFetched) {
            console.log("whole object:");
            console.log(apiFetched);
            console.log(JSON.stringify(apiFetched, null, 2));
            console.log(`url: ${apiFetched[MEDITATION_API_FETCH_KEY]["url"]}`);
            console.log(`fetchBody: ${apiFetched[MEDITATION_API_FETCH_KEY]["fetchBody"]}`);
        })
}

function handleMessages(message) {
    if (message.target === "background") {
        if (message.command === "download_stored_object") {
            browser.storage.local.get(message.storage_key)
                .then((itemsObject) => {
                    console.log(`background retrieved storage: ${message.storage_key}`);
                    let blob = new Blob([JSON.stringify(itemsObject)]);
                    let url = URL.createObjectURL(blob);
                    let timestampString = moment().format().replace(/:/g, '.');
                    console.log("timestamp: ", timestampString);
                    browser.downloads.download({
                        url: url,
                        filename: message.filename,
                        conflictAction: "overwrite",
                        saveAs: false
                    });
                    console.log(`background downloaded storage to file: ${message.filename}`);
                })
                .catch(reportError);
        } else if (message.command === "fetch_meditation_logs") {
            // checkStorage();
            browser.storage.local.get(MEDITATION_API_FETCH_KEY)
                .then((meditationAPIFetch) => {
                    console.log(`background retrieved storage for key: ${MEDITATION_API_FETCH_KEY}`);
                    console.log(JSON.stringify(meditationAPIFetch, null, 2));
                    console.log(`fetching: ${meditationAPIFetch[MEDITATION_API_FETCH_KEY]["url"]}`);
                    fetch(meditationAPIFetch[MEDITATION_API_FETCH_KEY]["url"],
                        meditationAPIFetch[MEDITATION_API_FETCH_KEY]["fetchBody"])
                        .then((response) => {
                            return response.json();
                        }).then((meditationJson) => {
                        let blob = new Blob([JSON.stringify(meditationJson)]);
                        let url = URL.createObjectURL(blob);
                        let timestampString = moment().format().replace(/:/g, '.');
                        console.log("timestamp: ", timestampString);
                        let filename = `tergar-meditation-logs-${timestampString}.json`;
                        browser.downloads.download({
                            url: url,
                            filename: filename,
                            conflictAction: "overwrite",
                            saveAs: false
                        });
                        console.log(`background downloaded storage to file: ${filename}`);
                    }).catch(reportError);
                })
                .catch(reportError);
        } else {
            console.log(`background got unexpected message: ${message}`);
        }
    }
}
