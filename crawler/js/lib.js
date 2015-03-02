//console.log("Lib loading...")

/*
 * Simulate.js from https://github.com/airportyh/simulate.js
 */
!function() {
	function extend(dst, src) {
		for ( var key in src)
			dst[key] = src[key]
		return src
	}
	var Simulate = {
		event : function(element, eventName) {
			if (document.createEvent) {
				var evt = document.createEvent("HTMLEvents")
				evt.initEvent(eventName, true, true)
				element.dispatchEvent(evt)
			} else {
				var evt = document.createEventObject()
				element.fireEvent('on' + eventName, evt)
			}
		},
		keyEvent : function(element, type, options) {
			var evt, e = {
				bubbles : true,
				cancelable : true,
				view : window,
				ctrlKey : false,
				altKey : false,
				shiftKey : false,
				metaKey : false,
				keyCode : 0,
				charCode : 0
			}
			extend(e, options)
			if (document.createEvent) {
				try {
					evt = document.createEvent('KeyEvents')
					evt.initKeyEvent(type, e.bubbles, e.cancelable, e.view,
							e.ctrlKey, e.altKey, e.shiftKey, e.metaKey,
							e.keyCode, e.charCode)
					element.dispatchEvent(evt)
				} catch (err) {
					evt = document.createEvent("Events")
					evt.initEvent(type, e.bubbles, e.cancelable)
					extend(evt, {
						view : e.view,
						ctrlKey : e.ctrlKey,
						altKey : e.altKey,
						shiftKey : e.shiftKey,
						metaKey : e.metaKey,
						keyCode : e.keyCode,
						charCode : e.charCode
					})
					element.dispatchEvent(evt)
				}
			}
		}
	}
	Simulate.keypress = function(element, chr) {
		var charCode = chr.charCodeAt(0)
		this.keyEvent(element, 'keypress', {
			keyCode : charCode,
			charCode : charCode
		})
	}
	Simulate.keydown = function(element, chr) {
		var charCode = chr.charCodeAt(0)
		this.keyEvent(element, 'keydown', {
			keyCode : charCode,
			charCode : charCode
		})
	}
	Simulate.keyup = function(element, chr) {
		var charCode = chr.charCodeAt(0)
		this.keyEvent(element, 'keyup', {
			keyCode : charCode,
			charCode : charCode
		})
	}
	Simulate.change = function(element) {
		var evt = document.createEvent("HTMLEvents");
		evt.initEvent("change", false, true);
		element.dispatchEvent(evt);

	}
	var events = [ 'click', 'focus', 'blur', 'dblclick', 'input', 'mousedown',
			'mousemove', 'mouseout', 'mouseover', 'mouseup', 'resize',
			'scroll', 'select', 'submit', 'load', 'unload', 'mouseleave' ]
	for (var i = events.length; i--;) {
		var event = events[i]
		Simulate[event] = (function(evt) {
			return function(element) {
				this.event(element, evt)
			}
		}(event))
	}
	if (typeof module !== 'undefined') {
		module.exports = Simulate
	} else if (typeof window !== 'undefined') {
		window.Simulate = Simulate
	} else if (typeof define !== 'undefined') {
		define(function() {
			return Simulate
		})
	}
}();

/*
 * object.watch polyfill
 * 
 * 2012-04-03
 * 
 * By Eli Grey, http://eligrey.com Public Domain. NO WARRANTY EXPRESSED OR
 * IMPLIED. USE AT YOUR OWN RISK.
 */

// object.watch
if (!Object.prototype.watch) {
	// console.log("Watch function created...")
	Object.defineProperty(Object.prototype, "watch", {
		enumerable : false,
		configurable : true,
		writable : false,
		value : function(prop, handler) {
			var oldval = this[prop], newval = oldval, getter = function() {
				return newval;
			}, setter = function(val) {
				oldval = val;
				return newval = handler.call(this, prop, oldval, val);
			};

			if (delete this[prop]) { // can't watch constants
				Object.defineProperty(this, prop, {
					get : getter,
					set : setter,
					enumerable : true,
					configurable : true
				});
			}
		}
	});
}

// object.unwatch
if (!Object.prototype.unwatch) {
	Object.defineProperty(Object.prototype, "unwatch", {
		enumerable : false,
		configurable : true,
		writable : false,
		value : function(prop) {
			var val = this[prop];
			delete this[prop]; // remove accessors
			this[prop] = val;
		}
	});
}

function callbackWrap(object, property, argumentIndex, wrapperFactory) {
	var original = object[property];
	object[property] = function() {
		wrapperFactory(this, arguments);
		return original.apply(this, arguments);
	}
	return original;
}

var max_waiting_time = 65000
var min_waiting_time = 0

function timingCallbackWrap(object, property, argumentIndex, wrapperFactory) {
	var original = object[property];

	object[property] = function() {
		if (arguments[1] > max_waiting_time) {
			arguments[1] = max_waiting_time
		}
		wrapperFactory(this, arguments);
		return original.apply(this, arguments);
	}
	return original;
}

function callInterceptionWrapper(object, property, argumentIndex,
		wrapperFactory) {
	var original = object[property];
	object[property] = function() {
		wrapperFactory(this, arguments);
		return null;
	}
	return original;
}

function XMLHTTPObserverOpen(elem, args) {
	resp = {
		"url" : args[1],
		"method" : args[0]
	};
	resp = JSON.stringify(resp)
	jswrapper.xmlHTTPRequestOpen(resp)
}

function XMLHTTPObserverSend(elem, args) {
	elems = []
	for (i = 0; i < args.length; i++) {
		elems.push(args[i])
	}
	resp = {
		"parameter" : elems
	};
	resp = JSON.stringify(resp)
	jswrapper.xmlHTTPRequestSend(resp)
}

function timeoutWrapper(elem, args) {
	function_id = MD5(args[0].toString());
	resp = {
		"function_id" : function_id,
		"time" : args[1]
	};
	resp = JSON.stringify(resp)
	jswrapper.timeout(resp)
}

function intervallWrapper(elem, args) {
	function_id = MD5(args[0].toString());
	resp = {
		"function_id" : function_id,
		"time" : args[1]
	};
	resp = JSON.stringify(resp)
	jswrapper.intervall(resp)
}

function getXPath(element) {
	// console.log(element.tagName + " : " + element.className + " ; " +
	// element.id)
	try {
		var xpath = '';
		for (; element && element.nodeType == 1; element = element.parentNode) {
			// console.log(element.tagName + " : " + element.className + " ; " +
			// element.id)
			var sibblings = element.parentNode.childNodes;
			var same_tags = []
			for (var i = 0; i < sibblings.length; i++) { // collecting same
															// tags
				if (element.tagName === sibblings[i].tagName) {
					same_tags[same_tags.length] = sibblings[i]
				}
			}
			var id = same_tags.indexOf(element) + 1
			id > 1 ? (id = '[' + id + ']') : (id = '');
			xpath = '/' + element.tagName.toLowerCase() + id + xpath;
		}
		console.log("XPATH: " + xpath)
		return xpath;
	} catch (e) {
		console.log("Error: " + e)
		return "";
	}
}

function addEventListenerWrapper(elem, args) {
	tag = elem.tagName
	dom_adress = "";
	id = elem.id;
	html_class = elem.className;
	console.log("New Addevent:" + tag + ":" + id + ":" + html_class + ":"
			+ args[0])
	dom_adress = getXPath(elem);
	if (dom_adress.indexOf("/html/body") == -1) {
		console.log("Domadress is not valid: " + dom_adress)
		return

	}
	function_id = MD5(args[1].toString())
	resp = {
		"event" : args[0],
		"function_id" : function_id,
		"addr" : dom_adress,
		"id" : id,
		"tag" : tag,
		"class" : html_class
	}
	resp = JSON.stringify(resp)
	jswrapper.add_EventListener_to_Element(resp)
	if (args[0] == "change") {
		inputs = elem.querySelectorAll("input");
		selects = elem.querySelectorAll("select");
		options = elem.querySelectorAll("option");

		for (i = 0; i < inputs.length; i++) {
			e = inputs[i];
			if (e.getAttribute("type") == "radio"
					|| e.getAttribute("type") == "checkbox") {
				tag = e.tagName
				id = e.id;
				html_class = e.className;
				dom_adress = getXPath(e);
				function_id = "";
				resp = {
					"event" : "change",
					"function_id" : function_id,
					"addr" : dom_adress,
					"id" : id,
					"tag" : tag,
					"class" : html_class
				}
				resp = JSON.stringify(resp)
				jswrapper.add_EventListener_to_Element(resp)
			}
		}
		for (i = 0; i < selects.length; i++) {
			s = selects[i];
			tag = s.tagName
			id = s.id;
			html_class = s.className;
			dom_adress = getXPath(s);
			function_id = "";
			resp = {
				"event" : "change",
				"function_id" : function_id,
				"addr" : dom_adress,
				"id" : id,
				"tag" : tag,
				"class" : html_class
			}
			resp = JSON.stringify(resp)
			jswrapper.add_EventListener_to_Element(resp)
		}
		for (xx = 0; xx < options.length; xx++) {
			o = options[i]
			tag = o.tagName
			id = o.id;
			html_class = o.className;
			dom_adress = getXPath(o);
			function_id = "";
			resp = {
				"event" : "change",
				"function_id" : function_id,
				"addr" : dom_adress,
				"id" : id,
				"tag" : tag,
				"class" : html_class
			}
			resp = JSON.stringify(resp)
			jswrapper.add_EventListener_to_Element(resp)
		}
	}
}

function bodyAddEventListenerWrapper(elem, args) {
	tag = elem.tagName
	dom_adress = "";
	id = elem.id;
	html_class = elem.className;
	console.log("New Addevent(Body):" + tag + ":" + id + ":" + html_class + ":"
			+ args[0])
	function_id = MD5(args[1].toString())
	dom_adress = "/html/body"
	resp = {
		"event" : args[0],
		"function_id" : function_id,
		"addr" : dom_adress,
		"id" : id,
		"tag" : tag,
		"class" : html_class
	}
	resp = JSON.stringify(resp)
	jswrapper.add_EventListener_to_Element(resp)

}

// console.log("Lib loading finished")
