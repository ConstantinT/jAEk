// This JS-Script wrapps the addEventListener-Function, that is used by JQuery
callbackWrap(Element.prototype, "addEventListener", 1, addEventListenerWrapper);
callbackWrap(Document.prototype, "addEventListener", 1,
		bodyAddEventListenerWrapper);