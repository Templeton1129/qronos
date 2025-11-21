import{c as D,B as M,a1 as R,U as H,s as K,a as B,O as F,a9 as V,a8 as O,aa as h,ab as U,ac as y,ax as k,a4 as S,m as r,aB as J,W as Z,b as l,e as c,o as s,j as I,y as N,d as b,n as Q,f as P,t as W,P as E,w,i as j,T as q,r as L,F as v,k as T,D as X,au as _,aC as $,ao as A,aD as ee,as as te}from"./index-B3e5YSF3.js";import{O as g,C as Y,F as ne}from"./index-D_I0lxb5.js";var ie=D`
    .p-menu {
        background: dt('menu.background');
        color: dt('menu.color');
        border: 1px solid dt('menu.border.color');
        border-radius: dt('menu.border.radius');
        min-width: 12.5rem;
    }

    .p-menu-list {
        margin: 0;
        padding: dt('menu.list.padding');
        outline: 0 none;
        list-style: none;
        display: flex;
        flex-direction: column;
        gap: dt('menu.list.gap');
    }

    .p-menu-item-content {
        transition:
            background dt('menu.transition.duration'),
            color dt('menu.transition.duration');
        border-radius: dt('menu.item.border.radius');
        color: dt('menu.item.color');
    }

    .p-menu-item-link {
        cursor: pointer;
        display: flex;
        align-items: center;
        text-decoration: none;
        overflow: hidden;
        position: relative;
        color: inherit;
        padding: dt('menu.item.padding');
        gap: dt('menu.item.gap');
        user-select: none;
        outline: 0 none;
    }

    .p-menu-item-label {
        line-height: 1;
    }

    .p-menu-item-icon {
        color: dt('menu.item.icon.color');
    }

    .p-menu-item.p-focus .p-menu-item-content {
        color: dt('menu.item.focus.color');
        background: dt('menu.item.focus.background');
    }

    .p-menu-item.p-focus .p-menu-item-icon {
        color: dt('menu.item.icon.focus.color');
    }

    .p-menu-item:not(.p-disabled) .p-menu-item-content:hover {
        color: dt('menu.item.focus.color');
        background: dt('menu.item.focus.background');
    }

    .p-menu-item:not(.p-disabled) .p-menu-item-content:hover .p-menu-item-icon {
        color: dt('menu.item.icon.focus.color');
    }

    .p-menu-overlay {
        box-shadow: dt('menu.shadow');
    }

    .p-menu-submenu-label {
        background: dt('menu.submenu.label.background');
        padding: dt('menu.submenu.label.padding');
        color: dt('menu.submenu.label.color');
        font-weight: dt('menu.submenu.label.font.weight');
    }

    .p-menu-separator {
        border-block-start: 1px solid dt('menu.separator.border.color');
    }
`,oe={root:function(e){var n=e.props;return["p-menu p-component",{"p-menu-overlay":n.popup}]},start:"p-menu-start",list:"p-menu-list",submenuLabel:"p-menu-submenu-label",separator:"p-menu-separator",end:"p-menu-end",item:function(e){var n=e.instance;return["p-menu-item",{"p-focus":n.id===n.focusedOptionId,"p-disabled":n.disabled()}]},itemContent:"p-menu-item-content",itemLink:"p-menu-item-link",itemIcon:"p-menu-item-icon",itemLabel:"p-menu-item-label"},se=M.extend({name:"menu",style:ie,classes:oe}),re={name:"BaseMenu",extends:K,props:{popup:{type:Boolean,default:!1},model:{type:Array,default:null},appendTo:{type:[String,Object],default:"body"},autoZIndex:{type:Boolean,default:!0},baseZIndex:{type:Number,default:0},tabindex:{type:Number,default:0},ariaLabel:{type:String,default:null},ariaLabelledby:{type:String,default:null}},style:se,provide:function(){return{$pcMenu:this,$parentInstance:this}}},G={name:"Menuitem",hostName:"Menu",extends:K,inheritAttrs:!1,emits:["item-click","item-mousemove"],props:{item:null,templates:null,id:null,focusedOptionId:null,index:null},methods:{getItemProp:function(e,n){return e&&e.item?J(e.item[n]):void 0},getPTOptions:function(e){return this.ptm(e,{context:{item:this.item,index:this.index,focused:this.isItemFocused(),disabled:this.disabled()}})},isItemFocused:function(){return this.focusedOptionId===this.id},onItemClick:function(e){var n=this.getItemProp(this.item,"command");n&&n({originalEvent:e,item:this.item.item}),this.$emit("item-click",{originalEvent:e,item:this.item,id:this.id})},onItemMouseMove:function(e){this.$emit("item-mousemove",{originalEvent:e,item:this.item,id:this.id})},visible:function(){return typeof this.item.visible=="function"?this.item.visible():this.item.visible!==!1},disabled:function(){return typeof this.item.disabled=="function"?this.item.disabled():this.item.disabled},label:function(){return typeof this.item.label=="function"?this.item.label():this.item.label},getMenuItemProps:function(e){return{action:r({class:this.cx("itemLink"),tabindex:"-1"},this.getPTOptions("itemLink")),icon:r({class:[this.cx("itemIcon"),e.icon]},this.getPTOptions("itemIcon")),label:r({class:this.cx("itemLabel")},this.getPTOptions("itemLabel"))}}},computed:{dataP:function(){return B({focus:this.isItemFocused(),disabled:this.disabled()})}},directives:{ripple:H}},ae=["id","aria-label","aria-disabled","data-p-focused","data-p-disabled","data-p"],le=["data-p"],de=["href","target"],ue=["data-p"],ce=["data-p"];function pe(t,e,n,o,d,i){var m=Z("ripple");return i.visible()?(s(),l("li",r({key:0,id:n.id,class:[t.cx("item"),n.item.class],role:"menuitem",style:n.item.style,"aria-label":i.label(),"aria-disabled":i.disabled(),"data-p-focused":i.isItemFocused(),"data-p-disabled":i.disabled()||!1,"data-p":i.dataP},i.getPTOptions("item")),[I("div",r({class:t.cx("itemContent"),onClick:e[0]||(e[0]=function(p){return i.onItemClick(p)}),onMousemove:e[1]||(e[1]=function(p){return i.onItemMouseMove(p)}),"data-p":i.dataP},i.getPTOptions("itemContent")),[n.templates.item?n.templates.item?(s(),b(P(n.templates.item),{key:1,item:n.item,label:i.label(),props:i.getMenuItemProps(n.item)},null,8,["item","label","props"])):c("",!0):N((s(),l("a",r({key:0,href:n.item.url,class:t.cx("itemLink"),target:n.item.target,tabindex:"-1"},i.getPTOptions("itemLink")),[n.templates.itemicon?(s(),b(P(n.templates.itemicon),{key:0,item:n.item,class:Q(t.cx("itemIcon"))},null,8,["item","class"])):n.item.icon?(s(),l("span",r({key:1,class:[t.cx("itemIcon"),n.item.icon],"data-p":i.dataP},i.getPTOptions("itemIcon")),null,16,ue)):c("",!0),I("span",r({class:t.cx("itemLabel"),"data-p":i.dataP},i.getPTOptions("itemLabel")),W(i.label()),17,ce)],16,de)),[[m]])],16,le)],16,ae)):c("",!0)}G.render=pe;function z(t){return be(t)||he(t)||me(t)||fe()}function fe(){throw new TypeError(`Invalid attempt to spread non-iterable instance.
In order to be iterable, non-array objects must have a [Symbol.iterator]() method.`)}function me(t,e){if(t){if(typeof t=="string")return x(t,e);var n={}.toString.call(t).slice(8,-1);return n==="Object"&&t.constructor&&(n=t.constructor.name),n==="Map"||n==="Set"?Array.from(t):n==="Arguments"||/^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)?x(t,e):void 0}}function he(t){if(typeof Symbol<"u"&&t[Symbol.iterator]!=null||t["@@iterator"]!=null)return Array.from(t)}function be(t){if(Array.isArray(t))return x(t)}function x(t,e){(e==null||e>t.length)&&(e=t.length);for(var n=0,o=Array(e);n<e;n++)o[n]=t[n];return o}var ve={name:"Menu",extends:re,inheritAttrs:!1,emits:["show","hide","focus","blur"],data:function(){return{overlayVisible:!1,focused:!1,focusedOptionIndex:-1,selectedOptionIndex:-1}},target:null,outsideClickListener:null,scrollHandler:null,resizeListener:null,container:null,list:null,mounted:function(){this.popup||(this.bindResizeListener(),this.bindOutsideClickListener())},beforeUnmount:function(){this.unbindResizeListener(),this.unbindOutsideClickListener(),this.scrollHandler&&(this.scrollHandler.destroy(),this.scrollHandler=null),this.target=null,this.container&&this.autoZIndex&&h.clear(this.container),this.container=null},methods:{itemClick:function(e){var n=e.item;this.disabled(n)||(n.command&&n.command(e),this.overlayVisible&&this.hide(),!this.popup&&this.focusedOptionIndex!==e.id&&(this.focusedOptionIndex=e.id))},itemMouseMove:function(e){this.focused&&(this.focusedOptionIndex=e.id)},onListFocus:function(e){this.focused=!0,!this.popup&&this.changeFocusedOptionIndex(0),this.$emit("focus",e)},onListBlur:function(e){this.focused=!1,this.focusedOptionIndex=-1,this.$emit("blur",e)},onListKeyDown:function(e){switch(e.code){case"ArrowDown":this.onArrowDownKey(e);break;case"ArrowUp":this.onArrowUpKey(e);break;case"Home":this.onHomeKey(e);break;case"End":this.onEndKey(e);break;case"Enter":case"NumpadEnter":this.onEnterKey(e);break;case"Space":this.onSpaceKey(e);break;case"Escape":this.popup&&(y(this.target),this.hide());case"Tab":this.overlayVisible&&this.hide();break}},onArrowDownKey:function(e){var n=this.findNextOptionIndex(this.focusedOptionIndex);this.changeFocusedOptionIndex(n),e.preventDefault()},onArrowUpKey:function(e){if(e.altKey&&this.popup)y(this.target),this.hide(),e.preventDefault();else{var n=this.findPrevOptionIndex(this.focusedOptionIndex);this.changeFocusedOptionIndex(n),e.preventDefault()}},onHomeKey:function(e){this.changeFocusedOptionIndex(0),e.preventDefault()},onEndKey:function(e){this.changeFocusedOptionIndex(k(this.container,'li[data-pc-section="item"][data-p-disabled="false"]').length-1),e.preventDefault()},onEnterKey:function(e){var n=S(this.list,'li[id="'.concat("".concat(this.focusedOptionIndex),'"]')),o=n&&S(n,'a[data-pc-section="itemlink"]');this.popup&&y(this.target),o?o.click():n&&n.click(),e.preventDefault()},onSpaceKey:function(e){this.onEnterKey(e)},findNextOptionIndex:function(e){var n=k(this.container,'li[data-pc-section="item"][data-p-disabled="false"]'),o=z(n).findIndex(function(d){return d.id===e});return o>-1?o+1:0},findPrevOptionIndex:function(e){var n=k(this.container,'li[data-pc-section="item"][data-p-disabled="false"]'),o=z(n).findIndex(function(d){return d.id===e});return o>-1?o-1:0},changeFocusedOptionIndex:function(e){var n=k(this.container,'li[data-pc-section="item"][data-p-disabled="false"]'),o=e>=n.length?n.length-1:e<0?0:e;o>-1&&(this.focusedOptionIndex=n[o].getAttribute("id"))},toggle:function(e,n){this.overlayVisible?this.hide():this.show(e,n)},show:function(e,n){this.overlayVisible=!0,this.target=n??e.currentTarget},hide:function(){this.overlayVisible=!1,this.target=null},onEnter:function(e){U(e,{position:"absolute",top:"0"}),this.alignOverlay(),this.bindOutsideClickListener(),this.bindResizeListener(),this.bindScrollListener(),this.autoZIndex&&h.set("menu",e,this.baseZIndex+this.$primevue.config.zIndex.menu),this.popup&&y(this.list),this.$emit("show")},onLeave:function(){this.unbindOutsideClickListener(),this.unbindResizeListener(),this.unbindScrollListener(),this.$emit("hide")},onAfterLeave:function(e){this.autoZIndex&&h.clear(e)},alignOverlay:function(){V(this.container,this.target);var e=O(this.target);e>O(this.container)&&(this.container.style.minWidth=O(this.target)+"px")},bindOutsideClickListener:function(){var e=this;this.outsideClickListener||(this.outsideClickListener=function(n){var o=e.container&&!e.container.contains(n.target),d=!(e.target&&(e.target===n.target||e.target.contains(n.target)));e.overlayVisible&&o&&d?e.hide():!e.popup&&o&&d&&(e.focusedOptionIndex=-1)},document.addEventListener("click",this.outsideClickListener,!0))},unbindOutsideClickListener:function(){this.outsideClickListener&&(document.removeEventListener("click",this.outsideClickListener,!0),this.outsideClickListener=null)},bindScrollListener:function(){var e=this;this.scrollHandler||(this.scrollHandler=new Y(this.target,function(){e.overlayVisible&&e.hide()})),this.scrollHandler.bindScrollListener()},unbindScrollListener:function(){this.scrollHandler&&this.scrollHandler.unbindScrollListener()},bindResizeListener:function(){var e=this;this.resizeListener||(this.resizeListener=function(){e.overlayVisible&&!F()&&e.hide()},window.addEventListener("resize",this.resizeListener))},unbindResizeListener:function(){this.resizeListener&&(window.removeEventListener("resize",this.resizeListener),this.resizeListener=null)},visible:function(e){return typeof e.visible=="function"?e.visible():e.visible!==!1},disabled:function(e){return typeof e.disabled=="function"?e.disabled():e.disabled},label:function(e){return typeof e.label=="function"?e.label():e.label},onOverlayClick:function(e){g.emit("overlay-click",{originalEvent:e,target:this.target})},containerRef:function(e){this.container=e},listRef:function(e){this.list=e}},computed:{focusedOptionId:function(){return this.focusedOptionIndex!==-1?this.focusedOptionIndex:null},dataP:function(){return B({popup:this.popup})}},components:{PVMenuitem:G,Portal:R}},ye=["id","data-p"],ge=["id","tabindex","aria-activedescendant","aria-label","aria-labelledby"],Le=["id"];function ke(t,e,n,o,d,i){var m=E("PVMenuitem"),p=E("Portal");return s(),b(p,{appendTo:t.appendTo,disabled:!t.popup},{default:w(function(){return[j(q,r({name:"p-connected-overlay",onEnter:i.onEnter,onLeave:i.onLeave,onAfterLeave:i.onAfterLeave},t.ptm("transition")),{default:w(function(){return[!t.popup||d.overlayVisible?(s(),l("div",r({key:0,ref:i.containerRef,id:t.$id,class:t.cx("root"),onClick:e[3]||(e[3]=function(){return i.onOverlayClick&&i.onOverlayClick.apply(i,arguments)}),"data-p":i.dataP},t.ptmi("root")),[t.$slots.start?(s(),l("div",r({key:0,class:t.cx("start")},t.ptm("start")),[L(t.$slots,"start")],16)):c("",!0),I("ul",r({ref:i.listRef,id:t.$id+"_list",class:t.cx("list"),role:"menu",tabindex:t.tabindex,"aria-activedescendant":d.focused?i.focusedOptionId:void 0,"aria-label":t.ariaLabel,"aria-labelledby":t.ariaLabelledby,onFocus:e[0]||(e[0]=function(){return i.onListFocus&&i.onListFocus.apply(i,arguments)}),onBlur:e[1]||(e[1]=function(){return i.onListBlur&&i.onListBlur.apply(i,arguments)}),onKeydown:e[2]||(e[2]=function(){return i.onListKeyDown&&i.onListKeyDown.apply(i,arguments)})},t.ptm("list")),[(s(!0),l(v,null,T(t.model,function(a,u){return s(),l(v,{key:i.label(a)+u.toString()},[a.items&&i.visible(a)&&!a.separator?(s(),l(v,{key:0},[a.items?(s(),l("li",r({key:0,id:t.$id+"_"+u,class:[t.cx("submenuLabel"),a.class],role:"none"},{ref_for:!0},t.ptm("submenuLabel")),[L(t.$slots,t.$slots.submenulabel?"submenulabel":"submenuheader",{item:a},function(){return[X(W(i.label(a)),1)]})],16,Le)):c("",!0),(s(!0),l(v,null,T(a.items,function(f,C){return s(),l(v,{key:f.label+u+"_"+C},[i.visible(f)&&!f.separator?(s(),b(m,{key:0,id:t.$id+"_"+u+"_"+C,item:f,templates:t.$slots,focusedOptionId:i.focusedOptionId,unstyled:t.unstyled,onItemClick:i.itemClick,onItemMousemove:i.itemMouseMove,pt:t.pt},null,8,["id","item","templates","focusedOptionId","unstyled","onItemClick","onItemMousemove","pt"])):i.visible(f)&&f.separator?(s(),l("li",r({key:"separator"+u+C,class:[t.cx("separator"),a.class],style:f.style,role:"separator"},{ref_for:!0},t.ptm("separator")),null,16)):c("",!0)],64)}),128))],64)):i.visible(a)&&a.separator?(s(),l("li",r({key:"separator"+u.toString(),class:[t.cx("separator"),a.class],style:a.style,role:"separator"},{ref_for:!0},t.ptm("separator")),null,16)):(s(),b(m,{key:i.label(a)+u.toString(),id:t.$id+"_"+u,item:a,index:u,templates:t.$slots,focusedOptionId:i.focusedOptionId,unstyled:t.unstyled,onItemClick:i.itemClick,onItemMousemove:i.itemMouseMove,pt:t.pt},null,8,["id","item","index","templates","focusedOptionId","unstyled","onItemClick","onItemMousemove","pt"]))],64)}),128))],16,ge),t.$slots.end?(s(),l("div",r({key:1,class:t.cx("end")},t.ptm("end")),[L(t.$slots,"end")],16)):c("",!0)],16,ye)):c("",!0)]}),_:3},16,["onEnter","onLeave","onAfterLeave"])]}),_:3},8,["appendTo","disabled"])}ve.render=ke;var we=D`
    .p-popover {
        margin-block-start: dt('popover.gutter');
        background: dt('popover.background');
        color: dt('popover.color');
        border: 1px solid dt('popover.border.color');
        border-radius: dt('popover.border.radius');
        box-shadow: dt('popover.shadow');
    }

    .p-popover-content {
        padding: dt('popover.content.padding');
    }

    .p-popover-flipped {
        margin-block-start: calc(dt('popover.gutter') * -1);
        margin-block-end: dt('popover.gutter');
    }

    .p-popover-enter-from {
        opacity: 0;
        transform: scaleY(0.8);
    }

    .p-popover-leave-to {
        opacity: 0;
    }

    .p-popover-enter-active {
        transition:
            transform 0.12s cubic-bezier(0, 0, 0.2, 1),
            opacity 0.12s cubic-bezier(0, 0, 0.2, 1);
    }

    .p-popover-leave-active {
        transition: opacity 0.1s linear;
    }

    .p-popover:after,
    .p-popover:before {
        bottom: 100%;
        left: calc(dt('popover.arrow.offset') + dt('popover.arrow.left'));
        content: ' ';
        height: 0;
        width: 0;
        position: absolute;
        pointer-events: none;
    }

    .p-popover:after {
        border-width: calc(dt('popover.gutter') - 2px);
        margin-left: calc(-1 * (dt('popover.gutter') - 2px));
        border-style: solid;
        border-color: transparent;
        border-bottom-color: dt('popover.background');
    }

    .p-popover:before {
        border-width: dt('popover.gutter');
        margin-left: calc(-1 * dt('popover.gutter'));
        border-style: solid;
        border-color: transparent;
        border-bottom-color: dt('popover.border.color');
    }

    .p-popover-flipped:after,
    .p-popover-flipped:before {
        bottom: auto;
        top: 100%;
    }

    .p-popover.p-popover-flipped:after {
        border-bottom-color: transparent;
        border-top-color: dt('popover.background');
    }

    .p-popover.p-popover-flipped:before {
        border-bottom-color: transparent;
        border-top-color: dt('popover.border.color');
    }
`,Ce={root:"p-popover p-component",content:"p-popover-content"},Oe=M.extend({name:"popover",style:we,classes:Ce}),Ie={name:"BasePopover",extends:K,props:{dismissable:{type:Boolean,default:!0},appendTo:{type:[String,Object],default:"body"},baseZIndex:{type:Number,default:0},autoZIndex:{type:Boolean,default:!0},breakpoints:{type:Object,default:null},closeOnEscape:{type:Boolean,default:!0}},style:Oe,provide:function(){return{$pcPopover:this,$parentInstance:this}}},Ee={name:"Popover",extends:Ie,inheritAttrs:!1,emits:["show","hide"],data:function(){return{visible:!1}},watch:{dismissable:{immediate:!0,handler:function(e){e?this.bindOutsideClickListener():this.unbindOutsideClickListener()}}},selfClick:!1,target:null,eventTarget:null,outsideClickListener:null,scrollHandler:null,resizeListener:null,container:null,styleElement:null,overlayEventListener:null,documentKeydownListener:null,beforeUnmount:function(){this.dismissable&&this.unbindOutsideClickListener(),this.scrollHandler&&(this.scrollHandler.destroy(),this.scrollHandler=null),this.destroyStyle(),this.unbindResizeListener(),this.target=null,this.container&&this.autoZIndex&&h.clear(this.container),this.overlayEventListener&&(g.off("overlay-click",this.overlayEventListener),this.overlayEventListener=null),this.container=null},mounted:function(){this.breakpoints&&this.createStyle()},methods:{toggle:function(e,n){this.visible?this.hide():this.show(e,n)},show:function(e,n){this.visible=!0,this.eventTarget=e.currentTarget,this.target=n||e.currentTarget},hide:function(){this.visible=!1},onContentClick:function(){this.selfClick=!0},onEnter:function(e){var n=this;U(e,{position:"absolute",top:"0"}),this.alignOverlay(),this.dismissable&&this.bindOutsideClickListener(),this.bindScrollListener(),this.bindResizeListener(),this.autoZIndex&&h.set("overlay",e,this.baseZIndex+this.$primevue.config.zIndex.overlay),this.overlayEventListener=function(o){n.container.contains(o.target)&&(n.selfClick=!0)},this.focus(),g.on("overlay-click",this.overlayEventListener),this.$emit("show"),this.closeOnEscape&&this.bindDocumentKeyDownListener()},onLeave:function(){this.unbindOutsideClickListener(),this.unbindScrollListener(),this.unbindResizeListener(),this.unbindDocumentKeyDownListener(),g.off("overlay-click",this.overlayEventListener),this.overlayEventListener=null,this.$emit("hide")},onAfterLeave:function(e){this.autoZIndex&&h.clear(e)},alignOverlay:function(){V(this.container,this.target,!1);var e=A(this.container),n=A(this.target),o=0;e.left<n.left&&(o=n.left-e.left),this.container.style.setProperty(ee("popover.arrow.left").name,"".concat(o,"px")),e.top<n.top&&(this.container.setAttribute("data-p-popover-flipped","true"),!this.isUnstyled&&te(this.container,"p-popover-flipped"))},onContentKeydown:function(e){e.code==="Escape"&&this.closeOnEscape&&(this.hide(),y(this.target))},onButtonKeydown:function(e){switch(e.code){case"ArrowDown":case"ArrowUp":case"ArrowLeft":case"ArrowRight":e.preventDefault()}},focus:function(){var e=this.container.querySelector("[autofocus]");e&&e.focus()},onKeyDown:function(e){e.code==="Escape"&&this.closeOnEscape&&(this.visible=!1)},bindDocumentKeyDownListener:function(){this.documentKeydownListener||(this.documentKeydownListener=this.onKeyDown.bind(this),window.document.addEventListener("keydown",this.documentKeydownListener))},unbindDocumentKeyDownListener:function(){this.documentKeydownListener&&(window.document.removeEventListener("keydown",this.documentKeydownListener),this.documentKeydownListener=null)},bindOutsideClickListener:function(){var e=this;!this.outsideClickListener&&$()&&(this.outsideClickListener=function(n){e.visible&&!e.selfClick&&!e.isTargetClicked(n)&&(e.visible=!1),e.selfClick=!1},document.addEventListener("click",this.outsideClickListener))},unbindOutsideClickListener:function(){this.outsideClickListener&&(document.removeEventListener("click",this.outsideClickListener),this.outsideClickListener=null,this.selfClick=!1)},bindScrollListener:function(){var e=this;this.scrollHandler||(this.scrollHandler=new Y(this.target,function(){e.visible&&(e.visible=!1)})),this.scrollHandler.bindScrollListener()},unbindScrollListener:function(){this.scrollHandler&&this.scrollHandler.unbindScrollListener()},bindResizeListener:function(){var e=this;this.resizeListener||(this.resizeListener=function(){e.visible&&!F()&&(e.visible=!1)},window.addEventListener("resize",this.resizeListener))},unbindResizeListener:function(){this.resizeListener&&(window.removeEventListener("resize",this.resizeListener),this.resizeListener=null)},isTargetClicked:function(e){return this.eventTarget&&(this.eventTarget===e.target||this.eventTarget.contains(e.target))},containerRef:function(e){this.container=e},createStyle:function(){if(!this.styleElement&&!this.isUnstyled){var e;this.styleElement=document.createElement("style"),this.styleElement.type="text/css",_(this.styleElement,"nonce",(e=this.$primevue)===null||e===void 0||(e=e.config)===null||e===void 0||(e=e.csp)===null||e===void 0?void 0:e.nonce),document.head.appendChild(this.styleElement);var n="";for(var o in this.breakpoints)n+=`
                        @media screen and (max-width: `.concat(o,`) {
                            .p-popover[`).concat(this.$attrSelector,`] {
                                width: `).concat(this.breakpoints[o],` !important;
                            }
                        }
                    `);this.styleElement.innerHTML=n}},destroyStyle:function(){this.styleElement&&(document.head.removeChild(this.styleElement),this.styleElement=null)},onOverlayClick:function(e){g.emit("overlay-click",{originalEvent:e,target:this.target})}},directives:{focustrap:ne,ripple:H},components:{Portal:R}},xe=["aria-modal"];function Ke(t,e,n,o,d,i){var m=E("Portal"),p=Z("focustrap");return s(),b(m,{appendTo:t.appendTo},{default:w(function(){return[j(q,r({name:"p-popover",onEnter:i.onEnter,onLeave:i.onLeave,onAfterLeave:i.onAfterLeave},t.ptm("transition")),{default:w(function(){return[d.visible?N((s(),l("div",r({key:0,ref:i.containerRef,role:"dialog","aria-modal":d.visible,onClick:e[3]||(e[3]=function(){return i.onOverlayClick&&i.onOverlayClick.apply(i,arguments)}),class:t.cx("root")},t.ptmi("root")),[t.$slots.container?L(t.$slots,"container",{key:0,closeCallback:i.hide,keydownCallback:function(u){return i.onButtonKeydown(u)}}):(s(),l("div",r({key:1,class:t.cx("content"),onClick:e[0]||(e[0]=function(){return i.onContentClick&&i.onContentClick.apply(i,arguments)}),onMousedown:e[1]||(e[1]=function(){return i.onContentClick&&i.onContentClick.apply(i,arguments)}),onKeydown:e[2]||(e[2]=function(){return i.onContentKeydown&&i.onContentKeydown.apply(i,arguments)})},t.ptm("content")),[L(t.$slots,"default")],16))],16,xe)),[[p]]):c("",!0)]}),_:3},16,["onEnter","onLeave","onAfterLeave"])]}),_:3},8,["appendTo"])}Ee.render=Ke;export{ve as a,Ee as s};
