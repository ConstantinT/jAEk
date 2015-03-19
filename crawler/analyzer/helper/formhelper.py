from models.form import HtmlForm, FormInput


class FormHelper():

    def extract_forms(self, frame):
        result = []
        forms = frame.findAllElements("form")
        for form in forms:
            action = form.attribute("action")
            method = form.attribute("method")
            dom_adress = form.evaluateJavaScript("getXPath(this)")
            form_params = self._extracting_information(form)
            result.append(HtmlForm(form_params, action, method, dom_adress))
        return result

    def _extracting_information(self, elem):
        result = []
        inputs = elem.findAll("input")
        radio_buttons = {} # key = name, value = array mit values

        for input_el in inputs:
            tag_name = input_el.tagName()
            if input_el.hasAttribute("type"):
                input_type = input_el.attribute("type")
                if input_type != "radio": #no radio button
                    if input_el.hasAttribute("name"):
                        name = input_el.attribute("name")
                    else:
                        name = ""
                    if input_el.hasAttribute("value"):
                        value = [input_el.attribute("value")]
                    else:
                        value = None
                    result.append(FormInput(tag_name, name, input_type, value))
                else: # input is radiobutton
                    name = input_el.attribute("name")
                    if name in radio_buttons: # Radio-Button name exists
                        radio_buttons[name].append(input_el.attribute("value"))
                    else: #Radiobutton name exists not
                        radio_buttons[name] = []
                        radio_buttons[name].append(input_el.attribute("value"))
        for key in radio_buttons:
            result.append(FormInput(tag_name, key, input_type, radio_buttons[key]))
        buttons = elem.findAll("button")
        for button in buttons:
            tag_name = button.tagName()
            if button.hasAttribute("type"):
                button_type = button.attribute("type")
            else:
                button_type = None
                logging.debug("Something mysterious must have happened...")
            if button.hasAttribute("name"):
                name = button.attribute("name")
            else:
                continue
            if button.hasAttribute("value"):
                value = [button.attribute("value")]
            else:
                value = None
                    #logging.debug(tag_name + " " + name + " " + input_type + " " + value)
            result.append(FormInput(tag_name, name, button_type, value))

        selects = elem.findAll("select")#<select> <option>
        for select in selects:
            select_name = select.attribute("name")
            options = select.findAll("option")
            values = []
            for option in options:
                values.append(option.attribute("value"))
            f_input = FormInput(select.tagName(), select_name, None, values)
            result.append(f_input)
        return result