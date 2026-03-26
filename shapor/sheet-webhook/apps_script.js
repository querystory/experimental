// Google Apps Script code for the QR Code Votes webhook.
// Deployed at: https://script.google.com/a/macros/querystory.ai/s/AKfycbyTiN89uIjXJc7RdwLt4eyPb8binSYjps7mZn2uCm8jQLekaNw9T8iE74zUCyR8irLJcA/exec
// Sheet: https://docs.google.com/spreadsheets/d/1dXuuKDWmEaVEolpeMiJhQONPMl9CKkqVgbd8A-WUM-A

function doPost(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data = JSON.parse(e.postData.contents);
  // Supports: vote="up"/"down" and/or stars=1-5
  sheet.appendRow([
    new Date(),
    data.file,
    data.vote || "",
    data.stars || "",
    data.voter || "anonymous"
  ]);
  return ContentService.createTextOutput(JSON.stringify({ok: true}))
    .setMimeType(ContentService.MimeType.JSON);
}

function doGet(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data = sheet.getDataRange().getValues();
  var votes = {};
  for (var i = 1; i < data.length; i++) {
    var file = data[i][1], vote = data[i][2], stars = data[i][3];
    if (!votes[file]) votes[file] = {up: 0, down: 0, stars: [], avg: 0};
    if (vote === "up") votes[file].up++;
    else if (vote === "down") votes[file].down++;
    if (stars) votes[file].stars.push(Number(stars));
  }
  for (var f in votes) {
    var s = votes[f].stars;
    votes[f].avg = s.length ? Math.round(s.reduce(function(a,b){return a+b},0) / s.length * 10) / 10 : 0;
    votes[f].count = s.length;
  }
  return ContentService.createTextOutput(JSON.stringify(votes))
    .setMimeType(ContentService.MimeType.JSON);
}
