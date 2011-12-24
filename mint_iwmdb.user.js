// http://wiki.greasespot.net/Metadata_Block
// ==UserScript==
// @name mint_iwmdb
// @description Mint: I want my data back
// @namespace http://www.madmode.com/gmscripts
// @include https://wwws.mint.com/transaction.event
// ==/UserScript==

// http://wiki.greasespot.net/Content_Script_Injection
// http://userscripts.org/scripts/source/100842.user.js
// function contentEval(source) { ...

function iwmdb(id) {
    alert(location.href);
    var tl_elt = document.getElementById(id);
    var btn = document.createElement('button');
    btn.textContent='IWMDB @@';
    tl_elt.parentNode.appendChild(btn);
    btn.addEventListener("click", function(event) {
        alert('IWMDB!');
        alert('$MW: ' + $MW);
    });
}

iwmdb("transaction-list");
