function action(worker, on, action, selector, original_color, highlight_color, params, on_success) {
    var url = '';
    if(on) {
        url = '/cmpp/personnes/gestion/' + worker + '/holidays/' + on + '/' + action + '/';
        $(selector).attr('style', 'background: ' + highlight_color);
    } else {
        url = '/cmpp/personnes/gestion/' + worker + '/holidays/' + action;
    }
    $("#holiday-dlg").load(url,
                           function() {
                               $(this).dialog({title: params.title,
                                               width: params.width,
                                               buttons: [{text: params.button_close,
                                                          click: function() {
                                                              $(this).dialog('close');
                                                              $(selector).attr('style', original_color);
                                                          }},{text: params.button_confirm,
                                                              click: function(){
                                                                  $.ajax({url: url,
                                                                          type: 'post',
                                                                          data: $('#holiday-dlg form').serialize()
                                                                         }).done(on_success)
                                                              }}]});
                           })
};

function add_holiday(worker) {
    params = {'title': 'Ajouter une absence', 'button_close': 'Fermer',
              'button_confirm': 'Ajouter', 'width': '500px'};

    on_success = function(response, status, xhr) {
        var content_type = xhr.getResponseHeader('content-type');
      if(content_type.indexOf('html') > -1) {
            $('#holiday-dlg form').html(response);
        } else {
            if(!response.err) {
                var result = response.content;
                var id = response.id;
                var li = $("<li id='" + id + "'></li>");
                var ul = $('<ul></ul>');
                $.each(result, function(i, e) {
                    console.log(e);
                    var item = $('<li class="' + e[0] + '">' + e[1] + '</li>');
                    ul.append(item);
                });
                var button_edit = $('<button class="icon-edit" data-action="edit" data-id="' + id + '"></button>');
                var button_delete = $('<button class="icon-remove" data-action="delete" data-id="' + id + '"></button>');
                var actions = $('<li class="actions"></li>');
                actions.append(button_edit, button_delete);
                ul.append(actions);
                li.append(ul);
                $("#holidays").append(li);
                $("#holiday-dlg").dialog("close");
            }
        }
    };
    action(worker, null, 'ajouter', null, null, null, params, on_success);
};

function delete_holiday(worker, holiday) {
    var selector = '#' + holiday + ' ul';
    var initial_color = $(selector).attr('style');
    var params = {'title': 'Supprimer une absence',
                  'button_close': 'Non', 'button_confirm': 'Oui',
                  'width': '450px'}

    on_success = function(response) {
        if(!response.err) {
            $('#' +  holiday).remove();
            $(selector).attr('style', initial_color);
            $("#holiday-dlg").dialog("close");
        }
    };
    action(worker, holiday, 'supprimer', selector, initial_color, '#f8b0b0', params, on_success);
};

function edit_holiday(worker, holiday) {
    var selector = '#' + holiday + ' ul';
    var initial_color = $(selector).attr('style');
    params = {'title': 'Éditer une absence',
              'button_close': 'Fermer', 'button_confirm': 'Mettre à jour',
              'width': '500px'}

    on_success = function(response, status, xhr) {
        var content_type = xhr.getResponseHeader('content-type');
        if(content_type.indexOf('html') > -1) {
            $('#holiday-dlg form').html(response);
        } else {
            if(!response.err) {
                $.each(response.content, function(i, e) {
                    $('#holidays #' + holiday + ' li.' + e[0]).html(e[1]);
                });
                $(selector).attr('style', initial_color);
                $("#holiday-dlg").dialog("close");
            }
        }}
    action(worker, holiday, 'editer', selector, initial_color,  '#af7', params, on_success);
};