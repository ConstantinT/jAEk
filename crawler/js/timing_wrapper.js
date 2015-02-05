// This JS-Script wrapps the addEventListener-Function, that is used by JQuery
timingCallbackWrap(window, "setTimeout", 0, timeoutWrapper);
timingCallbackWrap(window, "setInterval", 0, intervallWrapper);