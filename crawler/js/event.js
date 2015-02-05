var clickable = JSON.parse(clickable.attributes)

if (clickable.id != "") {
	var elem = document.getElementById(clickable.id);

}else{
	
}

var event = clickable.event; // TODO: Think about to split clickables, or
								// handle them here
if (event == "onclick" || event == "click") {
	elem.click();
	console.log("click()");
}
if (event == "onmouseover" || event == "mouseover") {
	elem.mouseover();
}
if (event == "onblur" || event == "blur") {
	elem.blur();
}
if (event == "onchange" || event == "change") {
	elem.change();
}
if (event == "onblclick" || event == "blclick") {
	elem.blclick();
}
if (event == "onfocus" || event == "focus") {
	elem.focus();
}
if (event == "onkeydown" || event == "keydown") {
	elem.keydown();
}
if (event == "onkeypress" || event == "keypress") {
	elem.keypress();
}
if (event == "onkeyup" || event == "keyup") {
	elem.keyup();
}
if (event == "onmousedown" || event == "mousedown") {
	elem.mousedown();
}
if (event == "onmousemove" || event == "mousemove") {
	elem.mousemove();
}
if (event == "onmouseout" || event == "mouseout") {
	elem.mouseout();
}
if (event == "onmouseup" || event == "mouseup") {
	elem.mouseup();
}