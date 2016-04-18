
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.keys import Keys
import time

TIME_TO_SLEEP = 0.1

# Get an element {%{

def monitor(browser):
    here = {'val': 0}
    LIMIT_COUNTER = 30
    found_message = set([])

    def counter():
        here['val'] += 1
        if here['val'] > LIMIT_COUNTER:
            browser.save_screenshot("waiting_too_long.png")

            for entry in browser.get_log('browser'):
                key = (entry['timestamp'], entry['message'])
                if key not in found_message:
                    print entry
                found_message.add(key)

    return counter

def get_input(browser, fieldname):
    # Most of the fields use IDs, however, some of them are included in a table with strange fields.
    #  We have to look for both
    my_input = None

    while not my_input:
        labels = get_elements_from_text(browser, tag_name="label", text=fieldname, wait=False)

        # we have a label!
        if labels:
            label = labels[0]
            idattr = label.get_attribute("for")
            my_input = get_element(browser, id_attr=idattr.replace('/', '\\/'), wait=True)
            break

        # do we have a strange table?
        table_header = get_elements_from_text(browser, class_attr='separator horizontal', tag_name="div", text=fieldname, wait=False)

        if not table_header:
            continue

        # => td
        table_header = table_header[0]

        table_node = table_header.find_elements_by_xpath("ancestor::tr[1]")
        if not table_node:
            continue

        element = table_node[0].find_elements_by_xpath("following-sibling::*[1]")
        if not element:
            continue

        # on peut maintenant trouver un input ou un select!
        for tagname in ["select", "input", "textarea"]:
            inputnode = element[0].find_elements_by_tag_name(tagname)
            if inputnode:
                my_input = inputnode[0]
                break

    return idattr, my_input

def get_elements(browser, tag_name=None, id_attr=None, class_attr=None, attrs=dict(), wait=False, atleast=0):
  '''
  This method fetch a node among the DOM based on its attributes.

  You can indicate wether this method is expected to wait for this element to appear.

  Be careful: this method also returns hidden elements!
  '''

  css_selector = ""

  css_selector += tag_name if tag_name is not None else "*"
  css_selector += ("." + class_attr) if class_attr is not None else ""
  css_selector += ("#" + id_attr) if id_attr is not None else ""

  if attrs:
    css_selector += "["
    item_number = 0

    for attr_name, value_attr in attrs.items():
      css_selector += "%(attr)s='%(value)s'" % dict(attr=attr_name, value=value_attr)

      item_number += 1
      if item_number != len(attrs):
        css_selector += ","

    css_selector += "]"

  nbtries = 0

  tick = monitor(browser)

  if not wait:
    elements = browser.find_elements_by_css_selector(css_selector)
  else:
    tick = monitor(browser)
    while True:
      tick()
      try:
        elements = browser.find_elements_by_css_selector(css_selector)
        if len(elements) > atleast:
            break

        #print("Wait 4 '%s'" % css_selector)
        #browser.save_screenshot("get_elements.png")
        time.sleep(TIME_TO_SLEEP)

        tick()

      except:
        #print("Wait 4 '%s'" % css_selector)
        #browser.save_screenshot("get_elements.png")
        time.sleep(TIME_TO_SLEEP)

      nbtries += 1

  return elements

def get_element(browser, tag_name=None, id_attr=None, class_attr=None, attrs=dict(), wait=False, position=None):
  elements = get_elements(browser, tag_name, id_attr, class_attr, attrs, wait, atleast=position or 0)

  if position is None:
      only_visible = filter(lambda x : x.is_displayed(), elements)

      return only_visible[0] if only_visible else elements[0]
  else:
    return elements[position]

def to_camel_case(text):
    words = text.split()
    words = map(lambda x : x[:1].upper() + x[1:].lower(), words)
    return ' '.join(words)

def get_elements_from_text(browser, tag_name, text, class_attr='', wait=True):
  '''
  This method fetch a node among the DOM based on its text.

  To find it, you must provide the name of the tag and its text.

  You can indicate wether this method is expected to wait for this element to appear.
  '''
  class_attr = (" and @class = '%s'" % class_attr) if class_attr else ''

  if not isinstance(tag_name, list):
    tag_name = [tag_name]
  possibilities = []

  for my_tag in tag_name:
    data = dict(class_attr=class_attr, tagname=my_tag, text=text)

    # we need to look for nodes "in the given node" when we select an option
    #  in a select and we don't want to select the other option
    xpath1_query = ".//%(tagname)s[normalize-space(.)='%(text)s'%(class_attr)s]" % data
    xpath2_query = ".//%(tagname)s//*[normalize-space(.)='%(text)s'%(class_attr)s]" % data
    possibilities.append(xpath1_query)
    possibilities.append(xpath2_query)

  xpath_query = '|'.join(possibilities)

  if not wait:
    ret = browser.find_elements_by_xpath(xpath_query)
    return filter(lambda x : x.is_displayed(), ret)
  else:
    tick = monitor(browser)
    while True:
      tick()

      elems = browser.find_elements_by_xpath(xpath_query)
      only_visible = filter(lambda x : x.is_displayed(), elems)

      if only_visible:
        return only_visible

      #print("Wait 4 '%s'" % xpath_query)
      time.sleep(TIME_TO_SLEEP)

      #browser.save_screenshot("get_elements_from_text.png")

def get_element_from_text(browser, tag_name, text, class_attr='', wait=True):
  '''
  This method fetch a node among the DOM based on its text.

  To find it, you must provide the name of the tag and its text.

  You can indicate wether this method is expected to wait for this element to appear.
  '''
  #FIXME: We cannot crash if an element is not found (especially an IndexError...)
  return get_elements_from_text(browser, tag_name, text, class_attr, wait)[0]

def get_column_position_in_table(maintable, columnname):
    elems = get_elements_from_text(maintable, tag_name="th", text=columnname, wait=False)
    if not elems:
        return None
    elem = elems[0]

    #FIXME: This is the maintable! It doesn't work that way.
    # The parent element is the element that generated this node but
    # it isn't the parent element in the DOM
    parent = elem.parent
    right_pos = None

    idtable = maintable.get_attribute("id")
    #FIXME: a table should always have an id, but... but who knows...
    assert idtable is not None

    data = dict(id=idtable)
    elements = maintable.find_elements_by_css_selector('#%(id)s thead th' % data)

    for pos, children in enumerate(elements):
        if children.get_attribute("id") == elem.get_attribute("id"):
            right_pos = pos
            break

    return right_pos

def get_table_row_from_hashes(world, keydict):
    columns = keydict.keys()

    #TODO: The pager is outside the table we look for above. As a result, we look
    #  for the external table, but that's not very efficient since we have to load
    #  them again afterwards...

    pagers = get_elements(world.browser, class_attr="gridview", tag_name="table")
    pagers = filter(lambda x : x.is_displayed(), pagers)
    for pager in pagers:
        elem = get_element(pager, class_attr="pager_info", tag_name="span")

        import re
        m = re.match('^\d+ - (?P<from>\d+) of (?P<to>\d+)$', elem.text.strip())
        do_it = False

        if m is None:
            do_it = True
        else:
            gp = m.groupdict()
            do_it = gp['from'] != gp['to']

        if do_it:
            elem.click()

            element = get_element(pager, tag_name="select", attrs=dict(action="filter"))
            select = Select(element)
            select.select_by_visible_text("unlimited")

            wait_until_not_loading(world.browser, wait=False)
    
    maintables = get_elements(world.browser, tag_name="table", class_attr="grid")
    maintables = filter(lambda x : x.is_displayed(), maintables)

    rows = []

    for maintable in maintables:

        #FIXME: We now that when a column is not found in one array, we look in the
        #        next one. This is not good since we could detect a column in another
        #        table...
        position_per_column = {}
        for column in columns:
            # We cannot normalize columns here because some columns don't follow
            #  the common convention
            pos_in_table = get_column_position_in_table(maintable, column)
            position_per_column[column] = pos_in_table

        if None in position_per_column.values():
            continue

        lines = get_elements(maintable, tag_name="tr", class_attr="grid-row")

        # we look for the first line with the right value
        for row_node in lines:

            # we have to check all the columns
            for column, position in position_per_column.iteritems():
                td_node = get_element(row_node, class_attr="grid-cell", tag_name="td", position=position)

                value = keydict[column]
                new_value = convert_input(world, value)

                if td_node.text.strip() != new_value:
                    break
            else:
                rows.append(row_node)

    return rows

#}%}

# Wait {%{
def wait_until_no_ajax(browser):
    tick = monitor(browser)
    while True:
        tick()
        time.sleep(TIME_TO_SLEEP)
        # sometimes, openobject doesn't exist in some windows
        try:
            ret = browser.execute_script('''

                function check(tab){
                    for(i in tab){
                        if(tab[i]){
                            return false;
                        }
                    }
                    return true;
                }

                if(!check(window.TOT)){
                    return "BLOCKED IN WINDOW";
                }

                elements = window.document.getElementsByTagName('iframe');

                totcount = (typeof window.openobject == 'undefined') ? 0 : window.openobject.http.AJAX_COUNT;


                for(var i = 0; i < elements.length; i++){
                    if(!check(elements[i].contentWindow.TOT)){
                        return "BLOCKED IN INFRAME " + i;
                    }

                    var local_ajaxcount = (typeof elements[i].contentWindow.openobject == 'undefined') ? 0 : elements[i].contentWindow.openobject.http.AJAX_COUNT;
                    if(local_ajaxcount > 0){
                        console.log("BLOCKED IN AJAXCOUNT WINDOW")
                    }

                    totcount += local_ajaxcount;
                }

                return totcount;
            ''')
        except WebDriverException as e:
            # If the script cannot be run, it means that the context is not available. We should
            #  stop at that time.
            print "EXCEPTION!!!!!"
            return

        #return ((typeof openobject == 'undefined') ? 0 : openobject.http.AJAX_COUNT) +
               #(window.TOT == null ? 0 : window.TOT) +
               #(($("iframe").first().size() == 0 || typeof $("iframe")[0].contentWindow.TOT == 'undefined') ? 0 : $("iframe")[0].contentWindow.TOT)

        if str(ret) != "0":
            #print "BOUCLE BLOCK", ret
            continue

        return

def repeat_until_no_exception(action, exception, *params):
    while True:
        try:
            return action(*params)
        except exception:
            time.sleep(TIME_TO_SLEEP)

def wait_until_element_does_not_exist(browser, get_elem):
  '''
  This method tries to click on the elem(ent) until the click doesn't raise en exception.
  '''

  tick = monitor(browser)
  while True:
    tick()
    try:
      #browser.save_screenshot("wait_until_element_does_not_exist.png")
      if not get_elem() or not get_elem().is_displayed():
        return
    except Exception as e:
      return
    time.sleep(TIME_TO_SLEEP)

def wait_until_not_displayed(browser, get_elem, accept_failure=False):
  '''
  This method tries to click on the elem(ent) until the click doesn't raise en exception.
  '''

  tick = monitor(browser)
  while True:
    tick()
    try:
      #browser.save_screenshot("wait_until_not_displayed.png")
      elem = get_elem()
      if not elem.is_displayed():
        return
    except Exception as e:
      if accept_failure:
        print "FAILURE ACCEPTED", e
        return
      else:
        print(e)
        raise
    time.sleep(TIME_TO_SLEEP)

def wait_until_not_loading(browser, wait=True):
  try:
    wait_until_not_displayed(browser, lambda : get_element(browser, tag_name="div", id_attr="ajax_loading", wait=wait), accept_failure=not wait)
  except:
    #print "GRRRRRR"
    return
#}%}

def convert_input(world, content, localdict=dict()):
    content = content.replace("{{ID}}", str(world.idrun))
    for key, value in localdict.iteritems():
        content = content.replace("{{%s}}" % key, value)
    return content

# Do something {%{
def click_on(elem_fetcher):
  '''
  This method tries to click on the elem(ent) until the click doesn't raise en exception.
  '''
  while True:
    try:
      elem = elem_fetcher()
      if elem and elem.is_displayed():
        elem.click()
      return
    except Exception as e:
      print(e)
      pass
    time.sleep(TIME_TO_SLEEP)

def action_write_in_element(txtinput, content):
    txtinput.clear()
    txtinput.send_keys((100*Keys.BACKSPACE) + content + Keys.TAB)

def action_select_option(txtinput, content):
    txtinput.click()
    option = get_element_from_text(txtinput, tag_name="option", text=content, wait=True)
    option.click()
    txtinput.click()

def select_in_field_an_option(browser, fieldelement, content):
    '''
    Find a field according to its label
    '''

    field, action, confirm = fieldelement()
    idattr = field.get_attribute("id")

    value_before = None
    ## we look for the value before (to check after)
    end_value = "_text"
    if idattr[-len(end_value):] == end_value:
        idvalue_before = idattr[:-len(end_value)]
        txtidinput = get_element(browser, id_attr=idvalue_before.replace('/', '\\/'), wait=True)
        value_before = txtidinput.get_attribute("value")

    txtinput, _, _ = fieldelement()

    action(txtinput, content)

    # We have to wait until the information is completed
    wait_until_no_ajax(browser)

#}%}

