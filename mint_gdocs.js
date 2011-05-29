
function make_budget_window(){
    var categories = Mint.CategorySearch.getJson();

    //http://www.quirksmode.org/js/popup.html
    ugly_but_reportedly_necessary_global = window.open('', 'budget_window',
						       'height=400, width=600');
    var d = ugly_but_reportedly_necessary_global.document;
    var b = d.body;

    var mk = function (p, n) {
	var e = d.createElement(n);
	p.appendChild(e);
	return e;
    }

    mk(b, 'h1').textContent = 'Budget';
    var t = mk(b, 'table');
    mk(mk(t, 'tr'), 'th').textContent = 'Category';
    categories.forEach(function(cat) {
	mk(mk(t, 'tr'), 'td').textContent = cat.value;
    });
}

make_budget_window();

/*
Mint.PlanningData.getJson(true, apr);
Mint.CategorySearch.getJson();

apr = new Date(2011, 03, 01);
// Fri Apr 01 2011 00:00:00 GMT-0500 (CDT)
Object
{
bu: Array[6]
0: Object
amt: 1522.5
bgt: 1250
cat: 1050996
ex: false
id: 25616372
pid: 30
st: 1
type: 0
}

*/
