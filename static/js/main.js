require(["/js/jquery-1.6.2.min.js", "net"], jQueryInit);

var game_started = false;
var start_time = 0;

var status = null;
var condition = null;
var role = null;
var matches = (/\/([a-f0-9]+)\//).exec(window.location.pathname);
var userkey = '0';
if (matches != null)
  userkey = matches[1];
console.info('userkey:' + userkey)

var tmpl_instructions = null;

String.prototype.capitalize = function() {
    return this.charAt(0).toUpperCase() + this.slice(1);
}

function resetProfileNames()
{
    var profiles = ['buyer', 'insurer', 'seller'];
    var names = ['Buyer', 'Mediator', 'Seller'];
    for (i in profiles)
        $('#' + profiles[i] + '_profile .profilename').html(names[i]);
}

function handleButton(evtname)
{
    return function(evt) {
        if ($(this).hasClass('pressed'))
            return false;
        
        var buttons = $(this);
        $(this).jConf({
            sText: $(this).prev('.button_explanation').html(),
            okBtn: 'Okay',
            noBtn: 'Cancel',
            evt: evt,
            callResult: function(data) {
                if (data.btnVal == 'Okay')
                {
                    events.addEvent(evtname, {});
                    setButtonPressed(buttons)
                }
            }
        });
        
    }
}

function setToken(role, state)
{
    var name = {'no': 'no_token', 'has': 'has_token', 'missing': 'token_missing'}[state];
    
    $('#' + role + '_token').attr('src', '/img/' + name + '.png')
        .removeClass('no_token has_token token_missing').addClass(name);
}

function setCurrentProfile(role)
{
    var matches = $('#' + role + '_profile');
    if (matches.length != 1)
        return;
    
    resetProfileNames();
    matches.find('span.profilename').html('You');
    matches.effect('highlight', {}, 750);
    
    if (role == 'buyer')
        $('#seller_chatbox').addClass('disabled');
    else if (role == 'seller')
        $('#buyer_chatbox').addClass('disabled');
    
    $('button').addClass('notyours').unbind('click');
    $('button.' + role).removeClass('notyours').addClass('yours');
    
    $('#instructions_role .title').addClass(role);
    $('#instructions_role').addClass(role).slideDown();
        
    switch (role)
    {
    case 'buyer':
        $('#buyer_chatinput').removeAttr('disabled');
        $('#buyer_send_seller').bind('click', handleButton('send_money_buyer_seller'));
        $('#buyer_send_insurer').bind('click', handleButton('send_money_buyer_insurer'));
        $('.profilebox .profiletokenlink').addClass('pointer');
    
        setToken('buyer', 'no');
        setToken('seller', 'has');
        
        $('#chat_info_buyer_insurer').css('display', 'block');
        break;
    
    case 'seller':
        $('#seller_chatinput').removeAttr('disabled');
        $('#seller_send_buyer').bind('click', handleButton('send_money_seller_buyer'));
        $('#seller_send_insurer').bind('click', handleButton('send_money_seller_insurer'));
        $('.profilebox.buyer .profiletokenlink').addClass('pointer');
        $('.profilebox.seller .profiletokenlink').bind('click', function (evt) {
            if ($(this).children().first().hasClass('has_token'))
            {
                events.addEvent('send_token', {});
                setToken('seller', 'no');
                setToken('buyer', 'yes');
            }
        })
    
        setToken('buyer', 'no');
        setToken('seller', 'has');
        $('#chat_info_seller_insurer').css('display', 'block');
        break;
    
    case 'insurer':
        $('.chatinput').removeAttr('disabled');
        $('#insurer_send_buyer').bind('click', handleButton('send_money_insurer_buyer'));
        $('#insurer_take_buyer').bind('click', handleButton('send_money_buyer_insurer'));
        $('#insurer_send_seller').bind('click', handleButton('send_money_insurer_seller'));
        $('#insurer_take_seller').bind('click', handleButton('send_money_seller_insurer'));
        $('.profilebox .profiletokenlink').addClass('pointer');
        
        $('#seller_token_info').css('display', 'block');
        $('#chat_info_insurer_buyer').css('display', 'block');
        $('#chat_info_insurer_seller').css('display', 'block');
        
        setToken('buyer', 'missing');
        setToken('seller', 'missing');
        break;
    }
}

function setButtonPressed(buttons)
{
    buttons.each(function (k, button) {
        button = $(button);
        button.addClass('pressed');
        
        if (button.hasClass('button_give'))
            button.find('span.action').html('25&cent; Given');
        else if (button.hasClass('button_take'))
            button.find('span.action').html('25&cent; Taken');
    });
}

function setTimer(seconds)
{
    var str_sec = '' + (seconds % 60);
    if (str_sec.length == 1)
        str_sec = '0' + str_sec;
    
    $('#timer').html(parseInt(seconds / 60) + ':' + str_sec);
}

wallets = {
    buyer: 0.25,
    seller: 0.25,
    insurer: 0.25,
};
function setWallet(role, amount)
{
    if (wallets[role] == undefined)
        wallets[role] = 0.0;
    
    wallets[role] += amount;
    $('#' + role + '_profile .profilewallet').html('$' + wallets[role].toFixed(2));
}

function jQueryInit()
{
    (function($){
      var ph = "PLACEHOLDER-INPUT";
      var phl = "PLACEHOLDER-LABEL";
      var boundEvents = false;
      var default_options = {
        labelClass: 'placeholder'
      };
      
      //check for native support for placeholder attribute, if so stub methods and return
      var input = document.createElement("input");
      if ('placeholder' in input) {
        $.fn.placeholder = $.fn.unplaceholder = function(){}; //empty function
        delete input; //cleanup IE memory
        return;
      };
      delete input;

      $.fn.placeholder = function(options) {
        bindEvents();

        var opts = $.extend(default_options, options)

        this.each(function(){
          var rnd=Math.random().toString(32).replace(/\./,'')
            ,input=$(this)
            ,label=$('<label style="position:absolute;display:none;top:0;left:0;"></label>');

          if (!input.attr('placeholder') || input.data(ph) === ph) return; //already watermarked

          //make sure the input tag has an ID assigned, if not, assign one.
          if (!input.attr('id')) input.attr('id') = 'input_' + rnd;

          label	.attr('id',input.attr('id') + "_placeholder")
              .data(ph, '#' + input.attr('id'))	//reference to the input tag
              .attr('for',input.attr('id'))
              .addClass(opts.labelClass)
              .addClass(opts.labelClass + '-for-' + this.tagName.toLowerCase()) //ex: watermark-for-textarea
              .addClass(phl)
              .text(input.attr('placeholder'));

          input
            .data(phl, '#' + label.attr('id'))	//set a reference to the label
            .data(ph,ph)		//set that the field is watermarked
            .addClass(ph)		//add the watermark class
            .after(label);		//add the label field to the page

          //setup overlay
          itemIn.call(this);
          itemOut.call(this);
        });
      };

      $.fn.unplaceholder = function(){
        this.each(function(){
          var	input=$(this),
            label=$(input.data(phl));

          if (input.data(ph) !== ph) return;
            
          label.remove();
          input.removeData(ph).removeData(phl).removeClass(ph);
        });
      };


      function bindEvents() {
        if (boundEvents) return;

        //prepare live bindings if not already done.
        $('.' + ph)
          .live('click',itemIn)
          .live('focusin',itemIn)
          .live('focusout',itemOut);
        bound = true;

        boundEvents = true;
      };

      function itemIn() {
        var input = $(this)
          ,label = $(input.data(phl));

        label.css('display', 'none');
      };

      function itemOut() {
        var that = this;

        //use timeout to let other validators/formatters directly bound to blur/focusout work first
        setTimeout(function(){
          var input = $(that);
          $(input.data(phl))
            .css('top', input.position().top + 'px')
            .css('left', input.position().left + 'px')
            .css('display', !!input.val() ? 'none' : 'block');
        }, 200);
      };

    }(jQuery));

    // Set the UI to the default blanked out state
    $(function() {
        resetProfileNames();
        $('button').addClass('notyours');
    });
    
    // Bind to events from the server
    events = require('net');

    events.bind('server', function(event) {
        if (event.name == 'uninvited' || event.name == 'gameover') {
            events.abort()
            location.href = '/quest/' + userkey + '/';
            return;
        }
        if (event.name == 'overqueued') {
            events.abort()
            location.href = '/overqueued/' + userkey + '/';
            return;
        }

        $('#eventlog').append(JSON.stringify(event));
        
        if (event.name == 'gamestart' && event.data.starttime != undefined)
        {
            start_time = parseInt(event.data.starttime);
        }
        if (event.name == 'time') {
            var newtime = 5*60 - (parseInt(event.time) - start_time);
            if (isNaN(window.timeleft) || Math.abs(newtime - window.timeleft) > 2)
                window.timeleft = newtime;
            else
                return;

            setTimer(window.timeleft);
            
            function timerFunc() {
                if (--window.timeleft <= 0)
                    window.clearInterval(window.timer);
                else {
                    window.timer = window.setTimeout(timerFunc, 1000);
                }
                
                setTimer(window.timeleft);
                if (window.timeleft % 60 == 0)
                    $('#timer').effect('highlight', 750);
            }
            
            clearTimeout(window.timer);
            window.timer = window.setTimeout(timerFunc, 1000);
        }
        else if (event.name != 'prequeue' && event.name != 'queued')
        {
            window.timeleft = parseInt(event.data.time) - start_time;
            setTimer(window.timeleft);
        }
    });

    events.bind('server:prequeue', function (data) {
        // Show the 'accept' message
    });

    events.bind('server:queued', function (data) {
        // Hide the accept message if it's still shown
        // Show the 'waiting for people' information
        // Show the countdown timer
    });

    events.bind('server:chat', function (data) {
        msgs = $('#'+data.chatbox+'_chatmessages')
        msgs.append('<div class="message '+data.from+(data.from==role?' yours':'')+'">' + data.message + '</div>')
        msgs.scrollTop(msgs[0].scrollHeight - msgs.height());
    });

    events.bind('server:gamestart', function (data) {
        if (game_started || data.role == undefined)
            return;
        game_started = true;
        
        role = data.role;
        condition = data.condition;
        
        setCurrentProfile(role);
        $('#content').show();
        $('#content').removeClass('disabled').addClass('enabled');
        $('#tmpl_instructions').tmpl(data).appendTo('#instructions_role .body');
        $('#instructions_role .title span').html(role.capitalize());

        
        var buy_info = 'Chat between ' + (role == 'buyer' ? 'you' : 'buyer') +
            ' and ' + (role == 'insurer' ? 'you' : 'mediator') + '.';
        var sell_info = 'Chat between ' + (role == 'seller' ? 'you' : 'seller') +
            ' and ' + (role == 'insurer' ? 'you' : 'mediator') + '.';
        
        $('#buyer_chatinput').attr('placeholder', buy_info);
        $('#seller_chatinput').attr('placeholder', sell_info);
        
        $('.chatinput[placeholder]').placeholder();
        
        switch (condition)
        {
        case 1:
            $('#buyer_send_seller').addClass('disabled');
            $('#seller_send_buyer').addClass('disabled');
            $('#insurer_take_seller').addClass('disabled');
            $('#insurer_take_buyer').addClass('disabled');
            break;
        
        case 2:
            $('#seller_send_buyer').addClass('disabled');
            $('#insurer_take_seller').addClass('disabled');
            $('#insurer_take_buyer').addClass('disabled');
            break;
        
        case 3:
            $('#seller_send_insurer').addClass('disabled');
            $('#buyer_send_insurer').addClass('disabled');
            $('#insurer_take_buyer').addClass('disabled');
            break;
        }
    });
    
    events.bind('server:send_money_buyer_seller', function () {
        setButtonPressed($('#buyer_send_seller'));
        setWallet('buyer', -0.25);
        setWallet('seller', 0.25);
    });
    
    events.bind('server:send_money_seller_insurer', function () {
        setButtonPressed($('#seller_send_insurer'));
        setWallet('seller', -0.25);
        setWallet('insurer', 0.25);
    });
    
    events.bind('server:send_money_buyer_insurer', function () {
        setButtonPressed($('#buyer_send_insurer'));
        setWallet('buyer', -0.25);
        setWallet('insurer', 0.25);
    });
    
    events.bind('server:send_money_insurer_buyer', function () {
        setButtonPressed($('#insurer_send_buyer'));
        setWallet('insurer', -0.25);
        setWallet('buyer', 0.25);
    });
    
    events.bind('server:send_money_insurer_seller', function () {
        setButtonPressed($('#insurer_send_seller'));
        setWallet('insurer', -0.25);
        setWallet('seller', 0.25);
    });
    
    events.bind('server:send_token', function () {
        setButtonPressed($('#insurer_send_seller'));
        setToken('buyer', 'has');
        setToken('seller', 'no');
    });

    // Bind to the chat box inputs
    function keydown(role) {
        return function(e) {
            var key = e.which;
            if (key == 13) {
                e.preventDefault();
                events.addEvent('chat', {'message': $(this).val(),
                                         'chatbox': role});
                $(this).val('');
            }
        }
    }
    
    $(function() {
        $('#buyer_chatinput').bind('keydown', keydown('buyer'))
        $('#seller_chatinput').bind('keydown', keydown('seller'))
        
        $('.chatinput').focus(function() {
            if (this.value === this.defaultValue)
                this.value = '';
        })
        .blur(function() {
            if (this.value === '')
                this.value = this.defaultValue;
        });
        
        // Bind to the approve accept button
        $('#approve').click(function() {
            // FIXME Check that the checkbox was selected
            events.addEvent('approve');
            // Hide the "Accept" message
        })
    });
    
    require(["/js/jquery-ui-1.8.14.min.js", "/js/jquery.tmpl.min.js", "/js/jConf-1.2.0.js"], function ()
    {
        // Start polling only when we have all the templates
        events.poll();
    });
    
    $(window).unload(function ()
    {
        // Pass
    });
}