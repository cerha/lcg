"use strict";window.lcg={}
lcg.KeyHandler=class{_keycodes={8:'Backspace',10:'Enter',13:'Enter',27:'Escape',32:'Space',33:'PageUp',34:'PageDown',35:'End',36:'Home',37:'Left',39:'Right',38:'Up',40:'Down'}
constructor(){this._keymap=this._define_keymap()}
_define_keymap(){return{}}
_event_key(event){let code=event.which
let key=undefined
if(code>=65&&code<=90){key=String.fromCharCode(code).toLowerCase()}else{key=this._keycodes[code]}
if(key){if(event.shiftKey){key='Shift-'+key}
if(event.altKey){key='Alt-'+key}
if(event.ctrlKey){key='Ctrl-'+key}}
return key}
_on_key_down(event){let command=this._keymap[this._event_key(event)]
if(command){event.preventDefault()
event.stopPropagation()
command.bind(this)(event,$(event.target))}}
_set_focus(element){if(element){setTimeout(()=>element.focus(),0)}}}
lcg.Widget=class extends lcg.KeyHandler{constructor(element){super()
this.element=this._element(element)
for(let e of this.element){e._lcg_widget_instance=this}}
_element(element){if(element instanceof jQuery){return element}else if(typeof element==='string'){return $('#'+element.replace('.','\\.'))}else{return $(element)}}
_get_object_by_name(name){let namespaces=name.split(".")
let last_name=namespaces.pop()
let context=window
for(const x of namespaces){context=context[x]}
return context[last_name]}
_ajax(settings,callback,failure){function wrap(func){return function(){try{return func.apply(this,arguments)}catch(e){console.log(e)}
return undefined}}
if(settings.form){let data=settings.form.serializeArray()
for(let param in settings.data){if(settings.data.hasOwnProperty(param)){let item=data.find(item=>item.name===param)
if(item!==undefined){item.value=settings.data[param]}else{data.push({name:param,value:settings.data[param]})}}}
settings.url||=settings.form.attr('action')
settings.method||=settings.form.attr('method')
settings.data=data}
document.body.style.cursor="wait"
let result=$.ajax(settings).always(()=>document.body.style.cursor="default")
if(callback){result=result.done(wrap(callback))}
if(failure){result=result.fail(wrap(failure))}
return result}}
lcg.Button=class extends lcg.Widget{constructor(element,callback){super(element)
if(typeof callback==='string'){callback=this._get_object_by_name(callback)}
if(callback){this.element.find('button').on('click',event=>{callback(this)
return false})}}}
lcg.Menu=class extends lcg.Widget{static _MANAGE_TABINDEX=true
constructor(element){super(element)
this._hidden=this.element.closest('[aria-hidden="true"]').length!==0
this._init_menu(this.element.find('ul').first())}
_init_menu(ul){this.items=this._init_items(ul,null)
let selected=this._initially_selected_item()
if(selected){this._select_item(selected)}}
_init_items(ul,parent){let items=[]
let base_id
if(parent){base_id=parent.attr('id')}else{base_id=this.element.attr('id')+'-item'}
for(let li of ul.children('li')){$(li).attr('role','presentation')
let item=$(li).children('a').first()
let prev=(items.length===0?null:items[items.length-1])
item.attr('id',base_id+'.'+(items.length+1))
this._init_item(item,prev,parent)
items.push(item)}
return items}
_init_item(item,prev,parent){item.attr('aria-selected','false')
item.on('keydown',this._on_key_down.bind(this))
item.on('click',event=>this._on_item_click(event,item))
if(this.constructor._MANAGE_TABINDEX||this._hidden){item.attr('tabindex','-1')}
item[0]._lcg_menu_item_data={prev:prev,next:null,parent:parent,submenu:null,menu:this,}
if(prev){this._data(prev).next=item}}
_data(item){return item[0]._lcg_menu_item_data}
_initially_selected_item(){let item
if(this.items.length!==0){let current=this.element.find('a.current').first()
if(current.length){item=current}else{item=this.items[0]}}else{item=null}
return item}
_active_descendant_parent(){let element=this.element.find('*[aria-activedescendant]')
if(!element.length){element=this.element}
return element}
_selected_item(){let p=this._active_descendant_parent()
let id=p.attr('aria-activedescendant')
if(id){let element=this._element(id)
if(element.length){return element}}
return null}
_select_item(item){let previously_selected_item=this._selected_item()
this._active_descendant_parent().attr('aria-activedescendant',item.attr('id'))
if(item.attr('aria-selected')!==undefined){item.attr('aria-selected','true')
if(previously_selected_item){previously_selected_item.attr('aria-selected','false')}}
if(this.constructor._MANAGE_TABINDEX&&!this._hidden){item.attr('tabindex','0')
if(previously_selected_item){previously_selected_item.attr('tabindex','-1')}}}
_expand_item(item){return false}
_on_item_click(event,item){this._cmd_activate(event,item)
return false}
_cmd_prev(event,item){this._set_focus(this._data(item).prev)}
_cmd_next(event,item){this._set_focus(this._data(item).next)}
_cmd_activate(event,item){return}
focus(){let item=this._selected_item()
if(item){this._expand_item(item)
this._set_focus(item)}}}
lcg.Notebook=class extends lcg.Menu{static _activation_callbacks={}
static _COOKIE='lcg_last_notebook_tab'
constructor(element){super(element)}
_define_keymap(){return{'Left':this._cmd_prev,'Right':this._cmd_next,'Enter':this._cmd_activate,'Space':this._cmd_activate}}
_initially_selected_item(){let current=this.element.find('.notebook-switcher li a.current').first()
if(current.length!==0){return current}
return(this._current_location_selected_item()||this._last_saved_selected_item()||this.items[0])}
_init_items(ul,parent){ul.attr('role','tablist')
return super._init_items(ul,parent)}
_init_item(item,prev,parent){super._init_item(item,prev,parent)
item.attr('role','tab')
let href=item.attr('href')
let page=$(href.substr(href.indexOf('#')))
item[0]._lcg_notebook_page=page
page[0]._lcg_notebook_item=item
page.find('h1,h2,h3,h4,h5,h6').hide()
page.hide()
page.addClass('notebook-page')
page.attr('role','tabpanel')
if(!page.attr('id')){page.attr('id',item.attr('id')+'-tabpanel')}
item.attr('aria-controls',page.attr('id'))}
_current_location_selected_item(){let match=self.location.href.match('#.+')
if(match){let parts=self.location.href.split('#',2)
let page=this.element.find('#'+parts[1])
if(page.length&&page[0]._lcg_notebook_item){return page[0]._lcg_notebook_item}}}
_last_saved_selected_item(){let cls=this.element.attr('class')
if(cls){let cookie=lcg.cookies.get(lcg.Notebook._COOKIE)
if(cookie){let parts=cookie.split(':',2)
if(parts[0]===cls){let page=this.element.find('#'+parts[1])
if(page.length&&page[0]._lcg_notebook_item){return page[0]._lcg_notebook_item}}}}
return null}
_select_item(item){let i,callback,repeat
let previously_selected_item=this._selected_item()
super._select_item(item)
if(!previously_selected_item||previously_selected_item[0]!==item[0]){if(previously_selected_item){previously_selected_item.removeClass('current')
previously_selected_item[0]._lcg_notebook_page.hide()}
item.addClass('current')
let page=item[0]._lcg_notebook_page
let cls=this.element.attr('class')
if(cls){let cookie=cls+':'+page.attr('id')
lcg.cookies.set(lcg.Notebook._COOKIE,cookie)}
page.show()
let callbacks=lcg.Notebook._activation_callbacks[page.attr('id')]
if(callbacks){for(let i=callbacks.length-1;i>=0;i--){callback=callbacks[i][0]
repeat=callbacks[i][1]
callback()
if(!repeat){callbacks.splice(i,1)}}}}}
_cmd_activate(event,item){this._select_item(item)
this._set_focus(item[0]._lcg_notebook_page)}}
lcg.Notebook.on_activation=function(page,callback,repeat){if(repeat===undefined){repeat=false}
let callbacks=lcg.Notebook._activation_callbacks[page.attr('id')]
if(!callbacks){callbacks=[]
lcg.Notebook._activation_callbacks[page.attr('id')]=callbacks}
callbacks.push([callback,repeat])}
lcg.FoldableTree=class extends lcg.Menu{constructor(element,toggle_button_tooltip){super(element)
this._expanded=false
$(this.element).attr('role','tree')
if(this._foldable&&toggle_button_tooltip){let button=$(`<button class="toggle-menu-expansion" title="${toggle_button_tooltip}">`).on('click',this._on_toggle_full_expansion.bind(this))
if(this._hidden){button.attr('tabindex','-1')}
$(this.element).find('ul').first().append(button)}}
_define_keymap(){return{'Up':this._cmd_up,'Ctrl-Shift-Up':this._cmd_up,'Down':this._cmd_down,'Ctrl-Shift-Down':this._cmd_down,'Shift-Up':this._cmd_prev,'Shift-Shift-Down':this._cmd_next,'Shift-Right':this._cmd_expand,'Shift-Left':this._cmd_collapse,'Right':this._cmd_expand,'Ctrl-Shift-Right':this._cmd_expand,'Left':this._cmd_collapse,'Ctrl-Shift-Left':this._cmd_collapse,'Escape':this._cmd_quit,'Enter':this._cmd_activate,'Space':this._cmd_activate}}
_init_menu(ul){this._foldable=false
super._init_menu(ul)}
_init_items(ul,parent){ul.attr('role','group')
return super._init_items(ul,parent)}
_init_item(item,prev,parent){super._init_item(item,prev,parent)
item.attr('role','treeitem')
let icon=item.find('.icon')
if(icon.length){icon.attr('role','presentation')}
let label=item.find('.label')
if(label.length){let label_id=item.attr('id')+'-label'
label.attr('id',label_id)
item.attr('aria-labelledby',label_id)}
let li=item.closest('li')
let submenu=li.find('ul').first()
if(submenu.length){if(li.hasClass('foldable')){if(!submenu.attr('id')){submenu.attr('id',item.attr('id')+'-submenu')}
item.attr('aria-controls',submenu.attr('id'))
let expander=li.find('.expander').first()
expander.attr('aria-controls',submenu.attr('id'))
expander.on('click',event=>this._on_expander_click(event,item))
expander.on('keydown',event=>{let key=this._event_key(event)
if(key==='Enter'||key==='Space'){event.preventDefault()
event.stopPropagation()
this._on_expander_click(event,item)}})
this._update_item(item,li.hasClass('expanded'))
this._foldable=true}
this._data(item).submenu=this._init_items(submenu,item)}}
_update_item(item,expanded){let li=item.closest('li')
let submenu=li.find('ul').first()
let expander=li.find('.expander').first()
let label=expander.attr(expanded?'data-collapse-label':'data-expand-label')
if(expanded){li.removeClass('collapsed')
li.addClass('expanded')}else{li.removeClass('expanded')
li.addClass('collapsed')}
submenu.attr('aria-hidden',expanded?'false':'true')
item.attr('aria-expanded',expanded?'true':'false')
expander.attr('aria-expanded',expanded?'true':'false')
expander.attr('title',label)
expander.find('.label').html(label)}
_expand_item(item){let expanded=false
if(item.closest('li').hasClass('collapsed')){this._update_item(item,true)
expanded=true}
if(this._data(item).parent){this._expand_item(this._data(item).parent)}
return expanded}
_collapse_item(item){if(item.closest('li').hasClass('expanded')){this._update_item(item,false)
return true}
return false}
_toggle_expansion(item){if(item.closest('li').hasClass('collapsed')){this._expand_item(item)}else{this._collapse_item(item)}}
_expand_recursively(item,expand){if(expand){this._expand_item(item)}else{this._collapse_item(item)}
const data=this._data(item)
if(data.submenu.length){this._expand_recursively(data.submenu[0],expand)}
if(data.next){this._expand_recursively(data.next,expand)}}
_next_item(item){let next
const data=this._data(item)
if(data.next){next=data.next}else if(data.parent&&this._data(data.parent).menu===this){next=this._next_item(data.parent)}
return next}
_cmd_up(event,item){let target=null
const data=this._data(item)
if(data.prev){target=data.prev
if(this._data(target).submenu&&data.prev.closest('li').hasClass('expanded')){let submenu=this._data(target).submenu
target=submenu[submenu.length-1]}}else{target=data.parent}
this._set_focus(target)}
_cmd_down(event,item){let target=null
const data=this._data(item)
if(data.submenu&&item.closest('li').hasClass('expanded')){target=this._data(item).submenu[0]}else{target=this._next_item(item)}
this._set_focus(target)}
_cmd_expand(event,item){const data=this._data(item)
if(!this._expand_item(item)&&data.submenu){this._set_focus(data.submenu[0])}}
_cmd_collapse(event,item){if(!this._collapse_item(item)){this._set_focus(this._data(item).parent)}}
_cmd_activate(event,item){self.location=item.attr('href')}
_cmd_quit(event,item){return}
_on_toggle_full_expansion(event){this._expanded=!this._expanded
this._expand_recursively(this.items[0],this._expanded)
let b=$(this.element).find('button.toggle-menu-expansion')
if(this._expanded){b.addClass('expanded')}else{b.removeClass('expanded')}}
_on_item_click(event,item){if($(event.target).closest('.label').length===0){this._toggle_expansion(item)
return false}
return super._on_item_click(event,item)}
_on_expander_click(event,item){this._toggle_expansion(item)
return false}}
lcg.PopupMenuBase=class extends lcg.Menu{constructor(element){super(element)
this._ignore_next_click=false}
_define_keymap(){return{'Up':this._cmd_prev,'Down':this._cmd_next,'Enter':this._cmd_activate,'Space':this._cmd_activate,'Escape':this._cmd_quit}}
_cmd_quit(event,item){this.dismiss()}
_on_click(event){let outside=$(event.target).closest('div')[0]!==this.element[0]
if(this._ignore_next_click&&!outside){this._ignore_next_click=false
return}
this.dismiss()
if(outside){return false}}
_on_touchend(event){if(!this._touch_moved){let element=$(event.target)
if(element.closest('div')[0]!==this.element[0]){this.dismiss()}else{this._cmd_activate(event,element.closest('a'))}
return false}}
popup(element,x,y,direction,selected_item_index){let active_menu=lcg.popup_menu
if(active_menu){active_menu.dismiss()
if(active_menu===this){return}}
lcg.popup_menu=this
this._popup_element=element
let menu=this.element
let selected_item
if(selected_item_index!==undefined&&selected_item_index!==null&&selected_item_index!==-1){selected_item=$(menu.find('ul').children()[selected_item_index]).find('a')}else{selected_item=menu.find('li.active a').first()}
this._select_item(selected_item)
menu.attr('style','display: none')
menu.css({left:x+'px',top:y+'px'})
if(direction==='up'){let total_height=menu.height()
let css_height=menu.height()
menu.css({height:0,display:'block',overflowY:'hidden'})
menu.animate({height:css_height+'px',top:y-total_height+'px',},{duration:200,done:()=>{menu.css({overflowY:'auto'})
this._set_focus(selected_item)},})}else{menu.slideToggle(200,()=>this._set_focus(selected_item))}
this._on_touchstart_handler=(e)=>{this._touch_moved=false}
this._on_touchmove_handler=(e)=>{this._touch_moved=true}
this._on_touchend_handler=this._on_touchend.bind(this)
this._on_click_handler=this._on_click.bind(this)
$(document).on('touchstart',this._on_touchstart_handler)
$(document).on('touchmove',this._on_touchmove_handler)
$(document).on('touchend',this._on_touchend_handler)
$(document).on('click',this._on_click_handler)
if(element){element.attr('aria-expanded','true')}}
dismiss(){$(document).off('touchstart',this._on_touchstart_handler)
$(document).off('touchmove',this._on_touchmove_handler)
$(document).off('touchend',this._on_touchend_handler)
$(document).off('click',this._on_click_handler)
this.element.hide()
lcg.popup_menu=null
let element=this._popup_element
if(element){element.attr('aria-expanded','false')
this._set_focus(element)}}}
lcg.popup_menu=null
lcg.PopupMenu=class extends lcg.PopupMenuBase{constructor(element,items,close_button_label){super(element)
this.items=items
this._close_button_label=close_button_label}
update(items){this.items=items
if(this.element.children().length){this.element.children().off()
this.element.empty()}}
create(){if(this.element.children().length!==0){return}
var ul=$('<ul role="menu">')
this.element.html(ul)
if(this.items.some(item=>item.icon)){this.element.addClass('with-icons')}
for(let attr of['aria-label','aria-activedescendant']){ul.attr(attr,this.element.attr(attr))
this.element.removeAttr(attr)}
let label_class='label'
for(let spec of this.items){let item=$(`<a href="${spec.uri || '#'}"><span class="label">${spec.label}</span></a>`)
let li=$('<li>').append(item)
if(spec.tooltip){item.attr('title',spec.tooltip)}
item[0]._lcg_popup_menu_item_spec=spec
if(spec.enabled===undefined||spec.enabled){li.addClass('active')}
if(spec.icon){item.prepend(`<span class="icon ${spec.icon}"></span>`)}
if(spec.cls){li.addClass(spec.cls)}
ul.append(li)}
let close=this._close_button_label;if(close){this.element.append($(`<a href="#" title="${close}" class="close-menu" role="button">${close}</a>`).on('click',e=>{this.dismiss();return false}))}
this._init_menu(ul)}
_init_item(item,prev,parent){super._init_item(item,prev,parent)
item.attr('role','menuitem')}
_on_key_down(event){this.element.addClass('keyboard-navigated')
super._on_key_down(event)}
_on_item_click(event,item){if(item.closest('li').hasClass('active')){this.dismiss()
let result=this._run_callback(event,item)
let uri=item[0]._lcg_popup_menu_item_spec.uri
if(uri&&result!==false){self.location=uri;}}
return false}
_cmd_activate(event,item){if(item.closest('li').hasClass('active')){this.dismiss()
this._run_callback(event,item)
if(!event.isPropagationStopped()){let uri=item[0]._lcg_popup_menu_item_spec.uri
if(uri){self.location=uri}}}}
_run_callback(event,item){let spec=item[0]._lcg_popup_menu_item_spec
let callback=spec.callback
if(callback){if(typeof callback==='string'){callback=this._get_object_by_name(callback)}
let args=[event,this._popup_element]
if(spec.callback_args){args=args.concat(spec.callback_args)}
return callback.apply(this,args)}}
popup(event,element,selected_item_index){if(event){event.stopPropagation()}
if(element===undefined){element=$(event.target)}
let menu=this.element
if(menu.children().length===0){this.create()}
let offset=element.offset()
let bottom=$(window).scrollTop()+$(window).height()
let menu_height=menu.height()
let direction,x,y
if(offset.top+element.height()+menu_height>bottom&&offset.top>menu_height){direction='up'}else{direction='down'}
if(event&&event.detail===1){x=Math.min(event.pageX-offset.left,element.width())
y=Math.min(event.pageY-offset.top,element.height())
menu.removeClass('keyboard-navigated')}else{x=0
y=direction==='up'?0:element.height()
menu.addClass('keyboard-navigated')}
if(offset.left+x+menu.width()>$(window).width()+window.pageXOffset){x-=menu.width()}
this._ignore_next_click=event&&event.which!==1
super.popup(element,x,y,direction,selected_item_index)}}
lcg.PopupMenuCtrl=class extends lcg.Widget{constructor(element,selector){super(element)
let menu=lcg.widget_instance(this.element.find('.popup-menu-widget'))
let ctrl=this.element.find('.invoke-menu')
ctrl.on('click',e=>menu.popup(e,ctrl))
ctrl.on('keydown',this._on_key_down.bind(this))
ctrl.find('.popup-arrow').on('click',e=>menu.popup(e,ctrl))
ctrl.attr('role','button')
ctrl.attr('aria-haspopup','true')
ctrl.attr('aria-expanded','false')
ctrl.attr('aria-controls',menu.element.attr('id'))
if(selector){this.element.closest(selector).on('contextmenu',e=>menu.popup(e,ctrl))}
this._menu=menu}
_define_keymap(){return{'Enter':this._cmd_activate,'Space':this._cmd_activate}}
_cmd_activate(event,element){this._menu.popup(undefined,element)}}
lcg.DropdownSelection=class extends lcg.PopupMenuBase{constructor(element,button_id,activation_callback,get_selected_item_index){super(element)
if(get_selected_item_index===undefined){get_selected_item_index=function(){return 0}}
this._activation_callback=activation_callback
this._get_selected_item_index=get_selected_item_index
this.element.attr('role','listbox')
let button=this._element(button_id)
this._button=button
button.attr('tabindex','0')
button.attr('role','button')
button.attr('aria-haspopup','true')
button.attr('aria-expanded','false')
button.attr('aria-controls',this.element.attr('id'))
button.on('click',this._on_button_click.bind(this))
button.on('keydown',this._on_button_key_down.bind(this))}
_on_button_key_down(event){let key=this._event_key(event)
if(key==='Enter'||key==='Space'||key==='Alt-Down'){this.dropdown()
return false}}
_on_button_click(event){if(this._button.attr('aria-expanded')==='true'){this.dismiss()}else{this.dropdown()}
return false}
_cmd_activate(event,item){this.dismiss()
this._activation_callback(item)}
_define_keymap(){return{'Up':this._cmd_prev,'Down':this._cmd_next,'Enter':this._cmd_activate,'Space':this._cmd_activate,'Escape':this._cmd_quit}}
_init_items(ul,parent){let items=super._init_items(ul,parent)
ul.attr('role','presentation')
return items}
_init_item(item,prev,parent){super._init_item(item,prev,parent)
item.attr('role','option')
item.on('mouseover',e=>this._select_item($(e.target)))}
_select_item(item){let previously_selected_item=this._selected_item()
super._select_item(item)
if(previously_selected_item&&previously_selected_item[0]!==item[0]){previously_selected_item.closest('li').removeClass('selected')}
item.closest('li').addClass('selected')
this._set_focus(item)}
dropdown(){let y,direction
let menu=this.element
let bottom=$(window).scrollTop()+$(window).height()
let height=menu.height()
let offset=this._button.offset()
if(offset.top+this._button.height()+height>bottom&&offset.top>height){y=0
direction='up'}else{y=this._button.height()
direction='down'}
let padding=menu.outerWidth()-menu.innerWidth()
menu.css({width:this._button.width()-padding+'px'})
this.popup(this._button,0,y,direction,this._get_selected_item_index())}}
lcg.Tooltip=class extends lcg.Widget{constructor(url,x,y){super($())
this._abort=false
this._ajax({url:url,method:'GET',},(response,status,xhr)=>{if(this._abort){return}
let div=this.element=$(`<div class="tooltip-widget">`)
let content_type=xhr.getResponseHeader('Content-Type')
if(content_type==='text/html'){div.html(response)}else if(content_type.substring(0,6)==='image/'){div.append(`<img src="${url}" border="0" style="vertical-align: middle">`)}else{return}
$(document.body).append(div)
div.css({left:(x+20)+'px',top:y+'px',position:'fixed',display:'block',})})}
remove(){this.element.remove()
this._abort=true}}
lcg.CollapsibleWidget=class extends lcg.Widget{constructor(element,collapsed){super(element)
let heading=this._heading=this._collapsible_heading()
let content=this._content=this._collapsible_content()
heading.append('<span class="icon">')
if(collapsed){this.element.addClass('collapsed')
content.hide()}else{this.element.addClass('expanded')}
heading.on('click',e=>{this.toggle()
return false})
if(!content.attr('id')){content.attr('id',this.element.attr('id')+'-collapsible-content')}
heading.attr('aria-expanded',collapsed?'false':'true')
heading.attr('aria-controls',content.attr('id'))}
_collapsible_heading(){}
_collapsible_content(){}
expanded(){return this.element.hasClass('expanded')}
expand(){this.element.removeClass('collapsed')
this.element.addClass('expanded')
this._heading.attr('aria-expanded','true')
this._content.slideDown(200)}
collapse(){this.element.removeClass('expanded')
this.element.addClass('collapsed')
this._heading.attr('aria-expanded','false')
this._content.slideUp(200)}
toggle(){if(this.element.hasClass('collapsed')){this.expand()}else{this.collapse()}}}
lcg.CollapsibleSection=class extends lcg.CollapsibleWidget{_collapsible_heading(){let heading=this.element.find('h1,h2,h3,h4,h5,h6,h7,h8').first()
heading.addClass('collapsible-section-heading')
let backref=heading.find('a.backref')
if(backref.length){backref.attr('href','')}
return heading}
_collapsible_content(){return this.element.find('div.section-content').first()}}
lcg.CollapsiblePane=class extends lcg.CollapsibleWidget{_collapsible_heading(){return this.element.find('.pane-title').find('a')}
_collapsible_content(){return this.element.find('.pane-content').first()}}
lcg.AudioPlayer=class extends lcg.Widget{constructor(elements,swf_uri){super(elements)
this._volume=0.8
this._player=this.element.find('.jp-player')
this._player.jPlayer({volumechange:this._on_player_volume_change.bind(this),play:this._on_player_play.bind(this),pause:this._on_player_pause.bind(this),timeupdate:this._on_player_time_update.bind(this),swfPath:swf_uri||undefined,supplied:"mp3",wmode:"window",useStateClassSkin:true,autoBlur:false,smoothPlayBar:true,keyEnabled:true,remainingDuration:true,captureDuration:false,toggleDuration:true,volume:this._volume})
this.element.find('.jp-volume-bar-value').html(Math.round(100*this._volume)+'%')
let play_button=this.element.find('button.play-pause')
this._play_label=play_button.attr('title')
this._pause_label=play_button.attr('data-pause-label')
this._remaining_label=this.element.find('.jp-duration').attr('title')
this._duration_label=this.element.find('.jp-duration').attr('data-duration-label')
this._bind('play-pause',this._play_pause)
this._bind('fast-forward',this._skip,true)
this._bind('rewind',this._skip,false)
this._bind('volume-up',this._change_volume,true)
this._bind('volume-down',this._change_volume,false)
this.element.find('.jp-duration').on('click',this._on_toggle_duration.bind(this))
play_button.on('keydown',this._on_key_down.bind(this))}
_bind(name,handler,arg){this.element.find('button.'+name).on('click',event=>{handler.bind(this)(arg)
$(event.target).focus()
return false})}
_define_keymap(){return{'Space':function(event,button){this._play_pause()},'Left':function(event,button){this._skip(false)},'Right':function(event,button){this._skip(true)},'Up':function(event,button){this._change_volume(true)},'Down':function(event,button){this._change_volume(false)},'Ctrl-Shift-Left':function(event,button){this._skip(false)},'Ctrl-Shift-Right':function(event,button){this._skip(true)},'Ctrl-Shift-Up':function(event,button){this._change_volume(true)},'Ctrl-Shift-Down':function(event,button){this._change_volume(false)}}}
_play_pause(){let status=this._player.data('jPlayer').status
let action=(status.paused?'play':'pause')
this._player.jPlayer(action)}
_seek(time,play){let command=(play?'play':'pause')
this._player.jPlayer(command,time)}
_skip(forward){let player=this._player
let status=player.data('jPlayer').status
let position=status.currentTime
let duration=status.duration
let playing=!status.paused
if(position!==null&&duration!==null){let skip=Math.max(Math.min(duration/20,30),3)
position+=skip*(forward?1:-1)
if(position>duration){return}
if(position<0){position=0}
this._seek(position,playing)}}
_change_volume(up){let player=this._player
if(up&&this._volume<1){this._volume=Math.min(this._volume+0.05,1)
player.jPlayer('volume',this._volume)}
if(!up&&this._volume>0){this._volume=Math.max(this._volume-0.05,0)
player.jPlayer('volume',this._volume)}}
_on_player_volume_change(event){this._volume=event.jPlayer.options.volume
this.element.find('.jp-volume-bar-value').html(Math.round(100*this._volume)+'%')}
_set_play_button_label(label){let button=this.element.find('button.play-pause')
button.attr('title',label)
button.find('span').html(label)}
_on_player_play(event){this._set_play_button_label(this._pause_label)}
_on_player_pause(event){this._set_play_button_label(this._play_label)}
_on_toggle_duration(event){let label
if(this._player.data('jPlayer').options.remainingDuration){label=this._remaining_label}else{label=this._duration_label}
this.element.find('.jp-duration').attr('title',label)
this.element.find('.duration-label').html(label)}
_on_player_time_update(event){let status=event.jPlayer.status}
_absolute_uri(uri){let origin=window.location.origin
if(!origin){origin=window.location.protocol+"//"+window.location.hostname
if(window.location.port&&window.location.port!==80){origin+=':'+window.location.port}}
if(uri.indexOf(origin)!==0){uri=origin+uri}
return uri}
_load_if_needed(uri){let status=this._player.data('jPlayer').status
if(status.media.mp3!==this._absolute_uri(uri)){this.load(uri)}}
_media_type(uri){let ext=uri.split('.').pop().toLowerCase()
if(ext==='mp3'){return{type:'mp3',media:'audio/mpeg'}}else if(ext==='ogg'||ext==='oga'){return{type:'oga',media:'audio/ogg codecs="vorbis"'}}else if(ext==='wav'||ext==='wave'){return{type:'wav',media:'audio/wav codecs="1"'}}else if(ext==='aac'||ext==='m4a'){return{type:'aac',media:'audio/mp4 codecs="mp4a.40.2"'}}else{return undefined}}
_can_play_audio(uri){let type=this._media_type(uri)
if(!type){return false}
let audio=this.element.find('audio')
if(audio.length){return!!(audio.canPlayType&&audio.canPlayType(type.media).replace(/no/,''))}else if(!this.element.find('.jp-no-solution').visible()){return(type.type=='mp3'||type.type=='aac')}else{return false}}
load(uri){this._player.jPlayer('setMedia',{mp3:uri})}
play(){this._player.jPlayer('play')}
bind_audio_control(element_id,uri){if(this._can_play_audio(uri)){let element=this._element(element_id)
element.on('click',event=>{this._load_if_needed(uri)
this._play_pause()
return false})
element.on('keydown',event=>{this._load_if_needed(uri)
this._on_key_down(event)})}}}
lcg.Cookies=class{constructor(path,domain){this.path=path||'/'
this.domain=domain||null}
set(name,value,days){let cookie=(name+'='+encodeURIComponent(String(value))+'; '+'SameSite=Lax; '+'Path='+escape(this.path))
if(days){let date=new Date()
date.setTime(date.getTime()+(days*24*60*60*1000))
cookie+='; Expires='+date.toGMTString()}
if(this.domain){cookie+='; Domain='+escape(this.domain)}
document.cookie=cookie}
get(name){return document.cookie.split('; ').reduce((r,v)=>{const parts=v.split('=')
return parts[0]===name?decodeURIComponent(parts[1]):r},'')}
clear(name){this.set(name,'',-1)}
clearAll(){for(let name of document.cookie.split(';').map(s=>s.split('=')[0].trim())){this.clear(name)}}}
lcg.cookies=new lcg.Cookies()
lcg.dedent=function(str){return(''+str).replace(/\n\s+/g,'');}
lcg.widget_instance=function(element){if(element instanceof jQuery){element=element[0]}else if(typeof element==='string'){element=document.getElementById(element)}
if(element&&element._lcg_widget_instance){return element._lcg_widget_instance}
return null}
lcg.lang=(document.documentElement.lang||navigator.language||'en').split('-')[0]
lcg.catalogs={}
lcg._catalogs_ready={}
lcg.gettext=function(domain){function locale_data(data){const meta=data['']||{}
const result={'':{'domain':domain,'lang':lcg.lang,'plural_forms':meta['Plural-Forms']||'nplurals=2; plural=(n != 1);'}}
for(const[key,value]of Object.entries(data)){if(key!==''){result[key]=value.slice(1)}}
return result}
if(!lcg._catalogs_ready[domain]){const link=document.querySelector(`link[rel=gettext][data-domain="${domain}"]`)
if(link){lcg._catalogs_ready[domain]=fetch(link.getAttribute('href')).then(r=>r.json()).then(data=>lcg.catalogs[domain]=new Jed({'domain':domain,'locale_data':{[domain]:locale_data(data)},})).catch(err=>{console.warn(`Could not load translations for domain ${domain}:`,err)})}else{lcg._catalogs_ready[domain]=Promise.resolve()}}
function translate(msgid){return lcg.catalogs[domain]?.gettext(msgid)??msgid}
translate.pgettext=function(context,msgid){return lcg.catalogs[domain]?.pgettext(context,msgid)??msgid}
translate.ngettext=function(singular,plural,n){let catalog=lcg.catalogs[domain]
if(catalog){return catalog.ngettext(singular,plural,n)}else{return(n===1?singular:plural)}}
translate.ready=lcg._catalogs_ready[domain]
return translate}