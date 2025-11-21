import{s as H}from"./index-BnzhCfOv.js";import{c as W,B as j,O as ae,P as le,b as T,o as h,F as re,k as ie,r as M,i,n as J,m as L,s as X,g as Y,q as Z,h as k,d as V,A as pe,w as g,j as t,D as y,Q as K,u as ue,I as de,v as ce,e as B,C as fe,t as me}from"./index-B3e5YSF3.js";import{s as ee,a as ge,b as ve}from"./index-nT30RV9H.js";import{g as ye,i as be,s as te,a as xe,b as he,c as we,d as q,e as ke}from"./index-DdqRGxFX.js";import{Q as Ie}from"./qrcode.vue.esm-DHWTV9f0.js";import{s as _e,a as Ce,b as Te,c as $e,d as Ae}from"./index-DQt60pV7.js";import{s as Se}from"./index-DGWKZG1Z.js";import{s as De}from"./index-StIlDHvi.js";import{_ as Ne}from"./_plugin-vue_export-helper-DlAUqK2U.js";import{u as Ge}from"./user-zDHzfMXm.js";var Ee=W`
    .p-inputotp {
        display: flex;
        align-items: center;
        gap: dt('inputotp.gap');
    }

    .p-inputotp-input {
        text-align: center;
        width: dt('inputotp.input.width');
    }

    .p-inputotp-input.p-inputtext-sm {
        text-align: center;
        width: dt('inputotp.input.sm.width');
    }

    .p-inputotp-input.p-inputtext-lg {
        text-align: center;
        width: dt('inputotp.input.lg.width');
    }
`,Pe={root:"p-inputotp p-component",pcInputText:"p-inputotp-input"},Ve=j.extend({name:"inputotp",style:Ee,classes:Pe}),Be={name:"BaseInputOtp",extends:ge,props:{readonly:{type:Boolean,default:!1},tabindex:{type:Number,default:null},length:{type:Number,default:4},mask:{type:Boolean,default:!1},integerOnly:{type:Boolean,default:!1}},style:Ve,provide:function(){return{$pcInputOtp:this,$parentInstance:this}}},ne={name:"InputOtp",extends:Be,inheritAttrs:!1,emits:["change","focus","blur"],data:function(){return{tokens:[]}},watch:{modelValue:{immediate:!0,handler:function(e){this.tokens=e?e.split(""):new Array(this.length)}}},methods:{getTemplateAttrs:function(e){return{value:this.tokens[e]}},getTemplateEvents:function(e){var s=this;return{input:function(d){return s.onInput(d,e)},keydown:function(d){return s.onKeyDown(d)},focus:function(d){return s.onFocus(d)},blur:function(d){return s.onBlur(d)},paste:function(d){return s.onPaste(d)}}},onInput:function(e,s){this.tokens[s]=e.target.value,this.updateModel(e),e.inputType==="deleteContentBackward"?this.moveToPrev(e):(e.inputType==="insertText"||e.inputType==="deleteContentForward"||ae()&&e instanceof CustomEvent)&&this.moveToNext(e)},updateModel:function(e){var s=this.tokens.join("");this.writeValue(s,e),this.$emit("change",{originalEvent:e,value:s})},moveToPrev:function(e){var s=this.findPrevInput(e.target);s&&(s.focus(),s.select())},moveToNext:function(e){var s=this.findNextInput(e.target);s&&(s.focus(),s.select())},findNextInput:function(e){var s=e.nextElementSibling;if(s)return s.nodeName==="INPUT"?s:this.findNextInput(s)},findPrevInput:function(e){var s=e.previousElementSibling;if(s)return s.nodeName==="INPUT"?s:this.findPrevInput(s)},onFocus:function(e){e.target.select(),this.$emit("focus",e)},onBlur:function(e){this.$emit("blur",e)},onClick:function(e){setTimeout(function(){return e.target.select()},1)},onKeyDown:function(e){if(!(e.ctrlKey||e.metaKey))switch(e.code){case"ArrowLeft":this.moveToPrev(e),e.preventDefault();break;case"ArrowUp":case"ArrowDown":e.preventDefault();break;case"Backspace":e.target.value.length===0&&(this.moveToPrev(e),e.preventDefault());break;case"ArrowRight":this.moveToNext(e),e.preventDefault();break;case"Enter":case"NumpadEnter":case"Tab":break;default:(this.integerOnly&&!(e.code!=="Space"&&Number(e.key)>=0&&Number(e.key)<=9)||this.tokens.join("").length>=this.length&&e.code!=="Delete")&&e.preventDefault();break}},onPaste:function(e){var s=e.clipboardData.getData("text");if(s.length){var m=s.substring(0,this.length);(!this.integerOnly||!isNaN(m))&&(this.tokens=m.split(""),this.updateModel(e))}e.preventDefault()}},computed:{inputMode:function(){return this.integerOnly?"numeric":"text"},inputType:function(){return this.mask?"password":"text"}},components:{OtpInputText:ee}};function Oe(n,e,s,m,d,r){var u=le("OtpInputText");return h(),T("div",L({class:n.cx("root")},n.ptmi("root")),[(h(!0),T(re,null,ie(n.length,function(c){return M(n.$slots,"default",{key:c,events:r.getTemplateEvents(c-1),attrs:r.getTemplateAttrs(c-1),index:c},function(){return[i(u,{value:d.tokens[c-1],type:r.inputType,class:J(n.cx("pcInputText")),name:n.$formName,inputmode:r.inputMode,variant:n.variant,readonly:n.readonly,disabled:n.disabled,size:n.size,invalid:n.invalid,tabindex:n.tabindex,unstyled:n.unstyled,onInput:function(I){return r.onInput(I,c-1)},onFocus:e[0]||(e[0]=function(f){return r.onFocus(f)}),onBlur:e[1]||(e[1]=function(f){return r.onBlur(f)}),onPaste:e[2]||(e[2]=function(f){return r.onPaste(f)}),onKeydown:e[3]||(e[3]=function(f){return r.onKeyDown(f)}),onClick:e[4]||(e[4]=function(f){return r.onClick(f)}),pt:n.ptm("pcInputText")},null,8,["value","type","class","name","inputmode","variant","readonly","disabled","size","invalid","tabindex","unstyled","onInput","pt"])]})}),128))],16)}ne.render=Oe;const Fe=""+new URL("google_play-N2cWJKDm.png",import.meta.url).href,Re=""+new URL("app-store-DxXaD0uQ.png",import.meta.url).href;var R,Q;function Ue(){return Q||(Q=1,R=function(){var n=document.getSelection();if(!n.rangeCount)return function(){};for(var e=document.activeElement,s=[],m=0;m<n.rangeCount;m++)s.push(n.getRangeAt(m));switch(e.tagName.toUpperCase()){case"INPUT":case"TEXTAREA":e.blur();break;default:e=null;break}return n.removeAllRanges(),function(){n.type==="Caret"&&n.removeAllRanges(),n.rangeCount||s.forEach(function(d){n.addRange(d)}),e&&e.focus()}}),R}var U,z;function Ke(){if(z)return U;z=1;var n=Ue(),e={"text/plain":"Text","text/html":"Url",default:"Text"},s="Copy to clipboard: #{key}, Enter";function m(r){var u=(/mac os x/i.test(navigator.userAgent)?"⌘":"Ctrl")+"+C";return r.replace(/#{\s*key\s*}/g,u)}function d(r,u){var c,f,I,v,b,p,o=!1;u||(u={}),c=u.debug||!1;try{I=n(),v=document.createRange(),b=document.getSelection(),p=document.createElement("span"),p.textContent=r,p.ariaHidden="true",p.style.all="unset",p.style.position="fixed",p.style.top=0,p.style.clip="rect(0, 0, 0, 0)",p.style.whiteSpace="pre",p.style.webkitUserSelect="text",p.style.MozUserSelect="text",p.style.msUserSelect="text",p.style.userSelect="text",p.addEventListener("copy",function(x){if(x.stopPropagation(),u.format)if(x.preventDefault(),typeof x.clipboardData>"u"){c&&console.warn("unable to use e.clipboardData"),c&&console.warn("trying IE specific stuff"),window.clipboardData.clearData();var C=e[u.format]||e.default;window.clipboardData.setData(C,r)}else x.clipboardData.clearData(),x.clipboardData.setData(u.format,r);u.onCopy&&(x.preventDefault(),u.onCopy(x.clipboardData))}),document.body.appendChild(p),v.selectNodeContents(p),b.addRange(v);var w=document.execCommand("copy");if(!w)throw new Error("copy command was unsuccessful");o=!0}catch(x){c&&console.error("unable to copy using execCommand: ",x),c&&console.warn("trying IE specific stuff");try{window.clipboardData.setData(u.format||"text",r),u.onCopy&&u.onCopy(window.clipboardData),o=!0}catch(C){c&&console.error("unable to copy using clipboardData: ",C),c&&console.error("falling back to prompt"),f=m("message"in u?u.message:s),window.prompt(f,r)}}finally{b&&(typeof b.removeRange=="function"?b.removeRange(v):b.removeAllRanges()),p&&document.body.removeChild(p),I()}return o}return U=d,U}var je=Ke();const Me=ye(je);var Le=W`
    .p-inputgroup,
    .p-inputgroup .p-iconfield,
    .p-inputgroup .p-floatlabel,
    .p-inputgroup .p-iftalabel {
        display: flex;
        align-items: stretch;
        width: 100%;
    }

    .p-inputgroup .p-inputtext,
    .p-inputgroup .p-inputwrapper {
        flex: 1 1 auto;
        width: 1%;
    }

    .p-inputgroupaddon {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: dt('inputgroup.addon.padding');
        background: dt('inputgroup.addon.background');
        color: dt('inputgroup.addon.color');
        border-block-start: 1px solid dt('inputgroup.addon.border.color');
        border-block-end: 1px solid dt('inputgroup.addon.border.color');
        min-width: dt('inputgroup.addon.min.width');
    }

    .p-inputgroupaddon:first-child,
    .p-inputgroupaddon + .p-inputgroupaddon {
        border-inline-start: 1px solid dt('inputgroup.addon.border.color');
    }

    .p-inputgroupaddon:last-child {
        border-inline-end: 1px solid dt('inputgroup.addon.border.color');
    }

    .p-inputgroupaddon:has(.p-button) {
        padding: 0;
        overflow: hidden;
    }

    .p-inputgroupaddon .p-button {
        border-radius: 0;
    }

    .p-inputgroup > .p-component,
    .p-inputgroup > .p-inputwrapper > .p-component,
    .p-inputgroup > .p-iconfield > .p-component,
    .p-inputgroup > .p-floatlabel > .p-component,
    .p-inputgroup > .p-floatlabel > .p-inputwrapper > .p-component,
    .p-inputgroup > .p-iftalabel > .p-component,
    .p-inputgroup > .p-iftalabel > .p-inputwrapper > .p-component {
        border-radius: 0;
        margin: 0;
    }

    .p-inputgroupaddon:first-child,
    .p-inputgroup > .p-component:first-child,
    .p-inputgroup > .p-inputwrapper:first-child > .p-component,
    .p-inputgroup > .p-iconfield:first-child > .p-component,
    .p-inputgroup > .p-floatlabel:first-child > .p-component,
    .p-inputgroup > .p-floatlabel:first-child > .p-inputwrapper > .p-component,
    .p-inputgroup > .p-iftalabel:first-child > .p-component,
    .p-inputgroup > .p-iftalabel:first-child > .p-inputwrapper > .p-component {
        border-start-start-radius: dt('inputgroup.addon.border.radius');
        border-end-start-radius: dt('inputgroup.addon.border.radius');
    }

    .p-inputgroupaddon:last-child,
    .p-inputgroup > .p-component:last-child,
    .p-inputgroup > .p-inputwrapper:last-child > .p-component,
    .p-inputgroup > .p-iconfield:last-child > .p-component,
    .p-inputgroup > .p-floatlabel:last-child > .p-component,
    .p-inputgroup > .p-floatlabel:last-child > .p-inputwrapper > .p-component,
    .p-inputgroup > .p-iftalabel:last-child > .p-component,
    .p-inputgroup > .p-iftalabel:last-child > .p-inputwrapper > .p-component {
        border-start-end-radius: dt('inputgroup.addon.border.radius');
        border-end-end-radius: dt('inputgroup.addon.border.radius');
    }

    .p-inputgroup .p-component:focus,
    .p-inputgroup .p-component.p-focus,
    .p-inputgroup .p-inputwrapper-focus,
    .p-inputgroup .p-component:focus ~ label,
    .p-inputgroup .p-component.p-focus ~ label,
    .p-inputgroup .p-inputwrapper-focus ~ label {
        z-index: 1;
    }

    .p-inputgroup > .p-button:not(.p-button-icon-only) {
        width: auto;
    }

    .p-inputgroup .p-iconfield + .p-iconfield .p-inputtext {
        border-inline-start: 0;
    }
`,qe={root:"p-inputgroup"},Qe=j.extend({name:"inputgroup",style:Le,classes:qe}),ze={name:"BaseInputGroup",extends:X,style:Qe,provide:function(){return{$pcInputGroup:this,$parentInstance:this}}},oe={name:"InputGroup",extends:ze,inheritAttrs:!1};function He(n,e,s,m,d,r){return h(),T("div",L({class:n.cx("root")},n.ptmi("root")),[M(n.$slots,"default")],16)}oe.render=He;var We={root:"p-inputgroupaddon"},Je=j.extend({name:"inputgroupaddon",classes:We}),Xe={name:"BaseInputGroupAddon",extends:X,style:Je,provide:function(){return{$pcInputGroupAddon:this,$parentInstance:this}}},se={name:"InputGroupAddon",extends:Xe,inheritAttrs:!1};function Ye(n,e,s,m,d,r){return h(),T("div",L({class:n.cx("root")},n.ptmi("root")),[M(n.$slots,"default")],16)}se.render=Ye;const Ze={class:"flex gap-2 items-center"},et={class:"flex gap-2 items-center"},tt={class:"flex flex-col gap-4 flex-1"},nt={class:"flex gap-2 items-center self-start"},ot={class:"flex pt-6 justify-end"},st={class:"my-class overflow-auto p-5 gap-2 border-2 border-dashed border-neutral-200 dark:border-neutral-700 rounded-lg bg-neutral-50 dark:bg-neutral-950 flex-1 flex flex-col font-medium"},at={class:"flex-1 flex flex-col gap-3 text-gray-600 dark:text-neutral-200 leading-relaxed"},lt={class:"flex gap-2 items-start text-sm"},rt={class:"space-y-3 text-sm"},it={class:"flex gap-2 items-start"},pt={key:0,class:"pi pi-check text-green-500"},ut={key:1,class:"pi pi-times text-red-500"},dt={class:"flex justify-between pt-6"},ct={class:"text-right"},ft={key:1,class:"text-center"},mt=Y({__name:"safetyDisclaimer.template",emits:["refreshIsFirstLogin"],setup(n,{emit:e}){const s=Z(),m=k(!1),d=k(""),r=k(!1),u=k(!1),c=k(!1),f=e,I=()=>{(r.value||c.value)&&(r.value=!1,c.value=!1)},v=async()=>{if(!(!d.value||u.value)){u.value=!0;try{const p=await he(d.value);u.value=!1,p.result===!0&&p.data===!0?(r.value=!0,s.add({severity:"success",summary:"提交成功！",life:3e3})):(c.value=!0,s.add({severity:"error",summary:"输入的声明码不正确",life:3e3}))}catch{c.value=!0}finally{u.value=!1}}},b=()=>{f("refreshIsFirstLogin")};return(p,o)=>{const w=te,x=Te,C=De,O=Ce,S=ve,D=Ae,N=xe,G=Se,a=se,l=ee,_=oe,$=$e,A=_e,E=H;return pe(be)()===!1?(h(),V(E,{key:0,class:"w-[600px]"},{content:g(()=>[i(A,{value:"1",class:"basis-[50rem]"},{default:g(()=>[i(O,{class:"flex justify-center gap-4"},{default:g(()=>[i(x,{value:1,asChild:""},{default:g(()=>[t("div",Ze,[i(w,{icon:"pi pi-volume-down",severity:"secondary",rounded:"",variant:"outlined"}),o[2]||(o[2]=t("div",null,"软件使用协议",-1))])]),_:1}),i(C,{class:"w-1/5"}),i(x,{value:2,asChild:""},{default:g(()=>[t("div",et,[i(w,{icon:"pi pi-pen-to-square",severity:"secondary",rounded:"",variant:"outlined"}),o[3]||(o[3]=t("div",null,"开源披露",-1))])]),_:1})]),_:1}),i($,{class:"h-[605px] p-0 pt-4"},{default:g(()=>[i(D,{value:"1",class:"h-full flex flex-col justify-between"},{default:g(({activateCallback:F})=>[t("div",tt,[o[5]||(o[5]=t("div",{class:"flex-1 p-5 gap-2 border-2 border-dashed border-neutral-200 dark:border-neutral-700 rounded-lg bg-neutral-50 dark:bg-neutral-950 flex flex-col justify-between items-center font-medium"},[t("div",{class:"flex-1 flex flex-col gap-3"},[t("div",{class:"text-lg font-semibold text-center"},[t("i",{class:"pi pi-volume-down mr-2"}),y("软件使用协议 ")]),t("div",{class:"space-y-2 text-gray-600 dark:text-neutral-200 leading-relaxed text-sm"},[t("p",null," 感谢您使用本产品。本软件本质上是一个实盘控制与管理器，用于简化和优化您在服务器上的实盘部署与操作体验。请您在继续使用前仔细阅读以下免责声明： "),t("p",null,[t("span",{class:"font-semibold"},"1. 风险自担："),y("我们不对您因使用本系统而造成的任何资金损失、交易错误或其他后果承担责任。数字资产交易具有高度风险，请谨慎操作。 ")]),t("p",null,[t("span",{class:"font-semibold"},"2. 核心逻辑完全开源："),y("本软件的前端、后端、部署脚本以及核心交易策略和实盘逻辑全部开源，您可完全自行审查与控制。 ")]),t("p",null,[t("span",{class:"font-semibold"},"3. 部署安全性取决于用户自身："),y("本软件的功能相当于一个控制面板，核心执行逻辑仍然依赖于您服务器上的实盘代码。如您有隐私顾虑、实盘金额较大，"),t("span",{class:"text-primary-500"},"强烈建议您下载完整的源码，自行审查并部署到独立服务器"),y("。我们论坛提供了完整的部署方案供您参考。 ")]),t("p",null,[t("span",{class:"font-semibold"},"4. 无数据收集："),y("本软件"),t("span",{class:"text-primary-500"},"不会收集任何用户数据"),y("，您所有的账户信息、密钥与配置均保存在您自己的服务器上。 ")]),t("p",null,[t("span",{class:"font-semibold"},"5. 知情同意："),y("继续使用即表示您已充分理解并同意以上所有条款。 ")])])])],-1)),t("div",nt,[i(S,{modelValue:m.value,"onUpdate:modelValue":o[0]||(o[0]=P=>m.value=P),binary:""},null,8,["modelValue"]),o[4]||(o[4]=t("label",{class:"font-semibold text-sm"},"我已充分理解并同意以上所有条款",-1))])]),t("div",ot,[i(w,{label:"下一步",icon:"pi pi-arrow-right",onClick:P=>F("2"),disabled:!m.value},null,8,["onClick","disabled"])])]),_:1}),i(D,{value:"2",class:"h-full flex flex-col justify-between"},{default:g(({activateCallback:F})=>[t("div",st,[t("div",at,[o[12]||(o[12]=t("div",{class:"text-lg font-semibold text-center"},"开源披露",-1)),o[13]||(o[13]=t("div",{class:"space-y-2 text-sm"},[t("p",null," 为了确保您完全了解本软件的运行方式，并确保您的实盘部署在您自己掌控之下，我们强烈建议您认真查看以下两个核心开源项目。 "),t("p",null," 本软件只是一个控制与交互界面，实际的交易执行与资金控制逻辑，全部依赖于以下开源代码库。请您务必自行阅读、理解，并确认是否接受相关实现方式再继续使用。 ")],-1)),o[14]||(o[14]=t("div",{class:"font-semibold text-sm"},"请完成以下操作",-1)),t("div",lt,[i(N,{value:"1"}),o[6]||(o[6]=t("span",{class:"leading-relaxed"},[y(" 1. 点击下方GitHub链接（前端/后端代码）"),t("br"),y("2. 在仓库中找到「code.txt」文件"),t("br"),y("3. 复制文件中的声明码"),t("br"),y("4. 返回本页面粘贴提交 ")],-1))]),o[15]||(o[15]=t("div",{class:"font-semibold text-sm"},"后端github代码地址:",-1)),i(G,{severity:"secondary",class:"py-2 text-sm"},{default:g(()=>o[7]||(o[7]=[t("a",{href:"https://github.com/Templeton1129/qronos",target:"_blank",class:"text-blue-500 text-sm"},"https://github.com/Templeton1129/qronos",-1)])),_:1,__:[7]}),o[16]||(o[16]=t("div",{class:"font-semibold text-sm"},"前端github代码地址:",-1)),i(G,{severity:"secondary",class:"py-2 text-sm"},{default:g(()=>o[8]||(o[8]=[t("a",{href:"https://github.com/Templeton1129/qronos-ui",target:"_blank",class:"text-blue-500 text-sm"},"https://github.com/Templeton1129/qronos-ui",-1)])),_:1,__:[8]}),t("div",rt,[t("div",it,[i(N,{value:"2"}),o[9]||(o[9]=t("span",null," 请粘贴从 GitHub 获取的声明码进行验证 ",-1))]),t("div",null,[i(_,{class:"w-[400px]"},{default:g(()=>[i(a,null,{default:g(()=>o[10]||(o[10]=[y("code")])),_:1,__:[10]}),i(l,{modelValue:d.value,"onUpdate:modelValue":o[1]||(o[1]=P=>d.value=P),modelModifiers:{trim:!0},placeholder:"请输入声明码",onKeyup:K(v,["enter"]),class:J({"!border-green-500":r.value,"!border-red-500":c.value}),onInput:I},null,8,["modelValue","class"]),i(a,null,{default:g(()=>[r.value?(h(),T("i",pt)):c.value?(h(),T("i",ut)):(h(),V(w,{key:2,loading:u.value,variant:"text",onClick:v,disabled:!d.value},{default:g(()=>o[11]||(o[11]=[y("确定")])),_:1,__:[11]},8,["loading","disabled"]))]),_:1})]),_:1})])])]),i(C),o[17]||(o[17]=t("div",{class:"space-y-2 leading-relaxed text-gray-600 dark:text-neutral-200 text-sm"},[t("div",{class:"font-semibold flex items-center gap-2"},[t("i",{class:"pi pi-volume-down text-green-400"}),t("span",null,"为什么这么做？")]),t("ul",{role:"list",class:"list-disc space-y-2 pl-4 text-sm"},[t("li",null,"我们希望您不是“盲用”本软件，而是真正清楚它做了什么。"),t("li",null," 本质上，您掌握的不是一个黑盒，而是完整透明的、可自审计的实盘系统。 "),t("li",null,"只有理解代码，才能真正控制自己的资金与交易风险。")])],-1))]),t("div",dt,[i(w,{severity:"secondary",icon:"pi pi-arrow-left",onClick:P=>F("1")},null,8,["onClick"]),t("div",ct,[i(w,{disabled:!r.value,onClick:b},{default:g(()=>o[18]||(o[18]=[y(" 开始使用 ")])),_:1,__:[18]},8,["disabled"])])])]),_:1})]),_:1})]),_:1})]),_:1})):(h(),T("div",ft," 请使用PC端电脑完成初始化操作，移动端设备暂不支持此功能 "))}}}),gt=Ne(mt,[["__scopeId","data-v-fe278646"]]),vt={key:0,class:"h-full w-full flex justify-center items-center p-4"},yt={class:"space-y-2 text-sm"},bt={class:"space-y-1 sm:space-y-2"},xt={class:"flex justify-center"},ht={class:"flex items-center justify-center space-x-2"},wt={class:"px-3 py-1 bg-gray-100 dark:bg-neutral-800 rounded text-sm font-mono tracking-wider"},kt={class:"space-y-1 sm:space-y-2"},It={class:"relative flex justify-center items-center"},_t={class:"relative flex justify-center items-center mb-2"},Vt=Y({__name:"login.page",setup(n){const e=fe(),s=Z(),m=Ge(),{gaToken:d,sessionGAtoken:r,userInfo:u,localStorageWxtoken:c}=ue(),f=k(""),I=k(""),v=k(""),b=k(null),p=k(null),o=k(!1);de(()=>{w(),C()});const w=async()=>{const a=await we();a.result===!0&&a.data!==null&&(b.value=a.data.is_first_use,m.setIsBoundGA(!a.data.is_first_use),p.value=a.data.is_declaration,a.data.is_first_use===!0&&x(),c.value=null)},x=()=>{d.value=null,r.value=null,c.value=null,u.value=null},C=()=>{if(b.value===!1)return;const a=localStorage.getItem("ga-secret-key");if(a)f.value=a;else{let _="";const $="ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";for(let A=0;A<16;A++)_+=$.charAt(Math.floor(Math.random()*$.length));f.value=_,localStorage.setItem("ga-secret-key",_)}const l=encodeURIComponent(f.value);I.value=`otpauth://totp/QRONOSUI:${l}?secret=${l}&issuer=QRONOSUI`},O=()=>{Me(f.value),s.add({severity:"success",summary:"复制成功",life:3e3})},S=ce(()=>v.value.length===6),D=async()=>{if(f.value&&S.value)try{o.value=!0;const a=await q(v.value,f.value);if(a.result===!0){let l=a.data;localStorage.removeItem("ga-secret-key"),G(l)}else o.value=!1,v.value=""}catch{o.value=!1}},N=async()=>{if(S.value)try{o.value=!0;const a=await q(v.value);if(a.result===!0){let l=a.data;localStorage.removeItem("ga-secret-key"),G(l)}else o.value=!1,v.value=""}catch{o.value=!1}},G=async a=>{if(a)if(d.value=(a==null?void 0:a.access_token)||"",r.value=(a==null?void 0:a.access_token)||"",(a==null?void 0:a.is_bind)===!0){const l=await ke();o.value=!1,l.result===!0&&(u.value=JSON.stringify(l.data),e.replace("/home")),v.value=""}else o.value=!1,u.value=null,e.replace("/bindWx")};return(a,l)=>{const _=te,$=ne,A=H;return b.value!==null&&p.value!==null?(h(),T("div",vt,[p.value===!1?(h(),V(gt,{key:0,onRefreshIsFirstLogin:w})):B("",!0),p.value===!0&&b.value===!0?(h(),V(A,{class:"w-full max-w-sm sm:max-w-md shadow-lg",key:"first-bind"},{header:g(()=>l[2]||(l[2]=[t("div",{class:"text-2xl font-semibold text-center mt-5"},"谷歌登录",-1)])),content:g(()=>[t("div",yt,[l[7]||(l[7]=t("div",{class:"space-y-1 sm:space-y-2"},[t("div",{class:"font-semibold"},"1. 请下载Google Authenticator"),t("p",{class:"text-xs"},'     Google Authenticator是一个动态密码工具，绑定后每次生成一个30秒更新一次的动态验证码， 用于登录安全验证。iOS用户登录AppStore，搜索"Authenticator"即可下载，而对于Android用户登录Google Play或使用手机浏览器搜索“Google Authenticator”下载。 '),t("div",{class:"h-10 flex justify-center items-center space-x-8"},[t("a",{href:"https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2",target:"_blank",class:"h-full"},[t("img",{src:Fe,alt:"Google Play",class:"h-full"})]),t("a",{href:"https://apps.apple.com/us/app/google-authenticator/id388497605",target:"_blank",class:"h-full"},[t("img",{src:Re,alt:"App Store",class:"h-full"})])])],-1)),t("div",bt,[l[4]||(l[4]=t("div",{class:"font-semibold"},"2. 扫描二维码或手动输入密钥",-1)),l[5]||(l[5]=t("p",{class:"text-xs"},"     打开Google Authenticator，扫描下方二维码或手动输入下方密钥添加验证令牌。密钥可用于在手机更换或丢失时验证Google Authenticator。请务必在绑定前备份以下密钥。 ",-1)),t("div",xt,[i(Ie,{class:"w-35 h-35 p-2 border border-gray-200 rounded-lg bg-white",value:I.value,level:"H","render-as":"svg"},null,8,["value"])]),t("div",ht,[l[3]||(l[3]=t("span",{class:"text-sm font-mediu"},"密钥:",-1)),t("span",wt,me(f.value),1),i(_,{icon:"pi pi-copy",size:"small","aria-label":"复制",onClick:O})])]),t("div",kt,[l[6]||(l[6]=t("div",{class:"font-semibold"},"3.请输入谷歌验证器中的验证码",-1)),t("div",It,[i($,{modelValue:v.value,"onUpdate:modelValue":l[0]||(l[0]=E=>v.value=E),integerOnly:"",length:6,onKeydown:K(D,["enter"])},null,8,["modelValue"])])])])]),footer:g(()=>[i(_,{label:"确认绑定",class:"w-full",disabled:!S.value,onClick:D},null,8,["disabled"])]),_:1})):B("",!0),p.value===!0&&b.value===!1?(h(),V(A,{class:"w-full max-w-sm sm:max-w-md shadow-lg",key:"second-verify"},{header:g(()=>l[8]||(l[8]=[t("div",{class:"text-2xl font-semibold text-center mt-5"},"谷歌登录",-1)])),content:g(()=>[t("div",null,[l[9]||(l[9]=t("div",{class:"text-center mb-2"},"请输入谷歌验证器中的验证码",-1)),t("div",_t,[i($,{modelValue:v.value,"onUpdate:modelValue":l[1]||(l[1]=E=>v.value=E),integerOnly:"",length:6,onKeydown:K(N,["enter"])},null,8,["modelValue"])])])]),footer:g(()=>[i(_,{label:"登录",severity:"primary",class:"w-full",disabled:!S.value,onClick:N,loading:o.value},null,8,["disabled","loading"])]),_:1})):B("",!0)])):B("",!0)}}});export{Vt as default};
