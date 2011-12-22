// http://wiki.greasespot.net/Metadata_Block
// ==UserScript==
// @name mint_iwmdb
// @description Mint: I want my data back
// @namespace http://www.madmode.com/gmscripts
// @include https://wwws.mint.com/transaction.event
// ==/UserScript==

// http://wiki.greasespot.net/Content_Script_Injection
// http://userscripts.org/scripts/source/100842.user.js
function contentEval(source) {
  // Check for function input.
  if ('function' == typeof source) {
    // Execute this function with no arguments, by adding parentheses.
    // One set around the function, required for valid syntax, and a
    // second empty set calls the surrounded function.
    source = '(' + source + ')();'
  }

  // Create a script node holding this  source code.
  var script = document.createElement('script');
  script.setAttribute("type", "application/javascript");
  script.textContent = source;

  // Insert the script node into the page, so it will run, and immediately
  // remove it to clean up.
  document.body.appendChild(script);
  document.body.removeChild(script);
}

function iwmdb(id) {
    var tl_elt = document.getElementById(id);
    var btn = document.createElement('button');
    btn.textContent='IWMDB';
    tl_elt.parentNode.appendChild(btn);
    btn.addEventListener("click", function(event) {
	contentEval( function() {
	    var tl = new $MW.TxnList("transaction-list",
				     {prefix: "transaction-"});

            $MC.useJson(C.JSON_TRANSACTIONS, function (trxs) {
                tl.setItemsData(trxs);
		alert('transaction data: ', trxs);
		alert('transaction data length: ', trxs.length);
            });
	});
    });
}

iwmdb("transaction-list");
