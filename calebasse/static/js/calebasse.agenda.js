function enable_events(base) {
      $(base).find('.textedit').on('keydown', function() {
          $('button', this).removeAttr("disabled");
      });
      $(base).find('.textedit button').on('click', function() {
          var textarea = $(this).prev();
          var span = textarea.prev()
          var btn = $(this)
          $.ajax({
              url: '/api/event/' + $(this).data("event-id") + '/?format=json',
              type: 'PATCH',
              contentType: 'application/json',
              data: '{"description": "' + textarea.val() + '"}',
              success: function(data) {
                  btn.attr('disabled', 'disabled');
                  span.html('Commentaire modifiée avec succès');
              }
          });
      });
      $(base).find('.appointment').on('click', function() {
          $('.textedit span', this).html('');
      });

      $(base).find('.remove-appointment').on('click', function() {
          var r = confirm("Etes-vous sûr de vouloir supprimer le rendez-vous " + $(this).data('rdv') + " ?");
          if (r == true)
          {
            $.ajax({
              url: $(this).data('url'),
              type: 'DELETE',
              success: function(data) {
                  window.location.reload(true);
                  return false;
              }
            });
           }
        return false;
      });
      $(base).find('.newrdv').click(function() {
          var participants = $('.person-item.active').map(function (i, v) { return $(v).data('worker-id'); });
          var qs = $.param({participants: $.makeArray(participants),
                            room: $.cookie('active-ressource-agenda'),
                            time: $(this).data('hour') }, true);
          var new_appointment_url = $(this).data('url') + "?" + qs;
          event_dialog(new_appointment_url, 'Nouveau rendez-vous', '850px', 'Ajouter');
      });
      $(base).find('.edit-appointment').click(function() {
          event_dialog("update-rdv/" + $(this).data('event-id') , 'Modifier rendez-vous', '850px', 'Modifier');
          return false;
      });
      $(base).find('.newevent').click(function() {
          var participants = $('.person-item.active').map(function (i, v) { return $(v).data('worker-id'); });
          var qs = $.param({participants: $.makeArray(participants),
                            room: $.cookie('active-ressource-agenda'),
                            time: $(this).data('hour') }, true);
          event_dialog($(this).data('url') + "?" + qs, 'Nouvel événement', '850px', 'Ajouter');
      });
      $(base).find('.edit-event').click(function() {
          event_dialog("update-event/" + $(this).data('event-id') , 'Modifier un événement', '850px', 'Modifier');
          return false;
      });
      $(base).find('#print-button').click(function() { window.print(); });

      $('.generate-mail-btn', base).click(function() {
        var url = '../../dossiers/' + $(this).data('dossier-id') + '/generate?event-id=' + $(this).data('event-id') + '&date=' + $(this).data('date');
        $('#ajax-dlg').load(url,
          function () {
            $(this).dialog({title: 'Générer un courrier', width: '500px',
                      buttons: [ { text: "Fermer",
                          click: function() { $(this).dialog("close"); } },
                      { text: "Générer",
                          click: function() { $("#ajax-dlg form").submit(); $(this).dialog("close"); } }]});
             $(this).find('.addresses input[type=radio]').change(function() {
               var address = $(this).data('contact-first-name') + ' ' + $(this).data('contact-last-name') + '\n';
               address += $(this).data('address-number') + ' ' + $(this).data('address-street') + '\n';
               address += $(this).data('address-zip-code') + ' ' + $(this).data('address-city')
               $('#id_address').val(address);
             });
             $('.addresses input[type=radio]').first().click();
          });
        return false;
      });
}

function reorder_disponibility_columns() {
    /* make sure column are ordered like tabs */
    var table_indexes = new Array();
    $('a.tab').each(function(a, b) {
        table_indexes.push($(b).data('id'));
    });
    rows = $('td#dispos table tr');
    for (var i=0; i<rows.length; i++) {
        tr = $(rows[i]);
        t = $.map(table_indexes,
                  function(v, i) { return $('.worker-' + v, tr)[0]; }).filter(
                  function(a) { if (a) return true; return false; });
        $('.agenda', tr).detach();
        $(tr).append(t);
    };
}

function toggle_worker(worker_selector) {
    var worker_id = $(worker_selector).data('worker-id');
    if (!worker_id) {
        return;
    }

    $(worker_selector).toggleClass('active');
    if (!($.cookie('agenda-worker-tabs'))) {
        $.cookie('agenda-worker-tabs', new Array(), { path: '/' });
    }
    if ($(worker_selector).hasClass('active')) {
        var tabs = $.cookie('agenda-worker-tabs');
        if ($.inArray($(worker_selector).attr('id'), tabs) == -1)
        {
            tabs.push($(worker_selector).attr('id'));
            $.cookie('agenda-worker-tabs', tabs, { path: '/' });
        }
    }
    else {
        var agendatabs = $.cookie('agenda-worker-tabs');
        $.each(agendatabs, function (i, value) {
            if (value == $(worker_selector).attr('id')) {
                agendatabs.splice(i, 1);
            }
        });
        $.cookie('agenda-worker-tabs', agendatabs, { path: '/' });
    }
    var target = $($(worker_selector).data('target'));
    target.toggle();

    var tab = $('#link-tab-worker-' + worker_id).parent().get(0);
    var tab_list = $(tab).parent().get(0);
    $(tab).detach().appendTo(tab_list);

    if ($('#tabs-worker-' + worker_id + ' .worker-tab-content-placeholder').length) {
        /* load worker appointments tab */
        $('#tabs-worker-' + worker_id).load('ajax-worker-tab/' + worker_id,
            function () {
	       $(this).children('div').accordion({active: false, autoHeight: false});
               enable_events(this);
            }
        );
        /* load worker disponibility column */
        $.get('ajax-worker-disponibility-column/' + worker_id,
            function(data) {
                var dispo_table_rows = $('td#dispos table tr');
                all_td = $(data).find('td');
                for (var i=0; i<all_td.length; i++) {
                    $(dispo_table_rows[i]).append(all_td[i]);
                }
            }
        );
    }
    return target.find('a.tab');
}

function toggle_ressource(ressource_selector) {
    var ressource_id = $(ressource_selector).data('ressource-id');
    if (!ressource_id) {
        return;
    }

    $(ressource_selector).toggleClass('active');
    if (!($.cookie('agenda-ressource-tabs'))) {
        $.cookie('agenda-ressource-tabs', new Array(), { path: '/' });
    }
    if ($(ressource_selector).hasClass('active')) {
        var tabs = $.cookie('agenda-ressource-tabs');
        if ($.inArray($(ressource_selector).attr('id'), tabs) == -1)
        {
            tabs.push($(ressource_selector).attr('id'));
            $.cookie('agenda-ressource-tabs', tabs, { path: '/' });
        }
    }
    else {
        var agendatabs = $.cookie('agenda-ressource-tabs');
        $.each(agendatabs, function (i, value) {
            if (value == $(ressource_selector).attr('id')) {
                agendatabs.splice(i, 1);
            }
        });
        $.cookie('agenda-ressource-tabs', agendatabs, { path: '/' });
    }
    var target = $($(ressource_selector).data('target'));
    target.toggle();

    var tab = $('#link-tab-ressource-' + ressource_id).parent().get(0);
    var tab_list = $(tab).parent().get(0);
    $(tab).detach().appendTo(tab_list);

    if ($('#tabs-ressource-' + ressource_id + ' .ressource-tab-content-placeholder').length) {
        /* load ressource appointments tab */
        $('#tabs-ressource-' + ressource_id).load('ajax-ressource-tab/' + ressource_id,
            function () {
	       $(this).children('div').accordion({active: false, autoHeight: false});
               enable_events(this);
            }
        );
        /* load ressource disponibility column */
        $.get('ajax-ressource-disponibility-column/' + ressource_id,
            function(data) {
                var dispo_table_rows = $('td#dispos table tr');
                $(data).find('td').each(function(a, b) {
                        $(dispo_table_rows[a]).append(b);
                    }
                );
                reorder_disponibility_columns();
            }
        );
    } else {
        reorder_disponibility_columns();
    }
    return target.find('a.tab');
}


function event_dialog(url, title, width, btn_text) {
          $('#rdv').load(url,
              function () {
                  function onsuccess(response, status, xhr, form) {
                      var parse = $(response);
                      if ($('.errorlist', parse).length != 0) {
                          $('#rdv').html(response);
                          $('#rdv form').ajaxForm({
                              success: onsuccess,
                          });
                          $('#rdv .datepicker-date').datepicker({dateFormat: 'd/m/yy', showOn: 'button'});
                          console.log('error');
                      } else {
                          console.log('success');
                          window.location.reload(true);
                      }
                  }
                  $('#rdv .datepicker-date').datepicker({dateFormat: 'd/m/yy', showOn: 'button'});
                  $('#id_description').attr('rows', '3');
                  $('#id_description').attr('cols', '30');
		  var deck = $('#id_participants_on_deck');
                  $(deck).bind('added', function() {
                      var added = $(deck).find('div:last');
                      var t = added.attr('id').indexOf('_group:');
                      if ( t == -1) return;
                      var query = added.attr('id').substr(t+1);

                      /* remove group element and fake id */
                      added.remove();
                      var val = $('#id_participants').val();
                      $('#id_participants').val(val.substr(0, val.substr(0, val.length-1).lastIndexOf('|')+1));

                      /* add all workers */
                      var receive_result = $('#id_participants_text').autocomplete('option', 'select');
                      $.getJSON($('#id_participants_text').autocomplete('option', 'source') + '?term=' + query,
                          function(data) {
                              $.each(data, function(key, val) {
                                  if (key==0) return; /* ignore first element as it's the group itself */
                                  var ui = Object();
                                  ui.item = val;
                                  receive_result(null, ui);
                              });
                      });
                  });
                  $('form', this).ajaxForm({
                      success: onsuccess
                  });
                  $(this).dialog({title: title,
                      width: width,
                      buttons: [ { text: "Fermer",
                          click: function() { $(this).dialog("close"); } },
                      { text: btn_text,
                          click: function() { $("#rdv form").submit(); } }]});
              });
}

(function($) {
  $(function() {
      $('#tabs').tabs();

      $('#tabs').ajaxStop(function() { reorder_disponibility_columns(); });

      if ($('.person-item').length) {
          $('.person-item').on('click', function() {
              var target = toggle_worker(this);
              if ($(target).is(':visible')) {
                  $(target).click();
              }
              if ($('#filtre input').val()) {
                  $('#filtre input').val('');
                  $('#filtre input').keyup();
                  $('#filtre input').focus();
              }
          });

          $('a.tab').click(function() {
              $.cookie('active-worker-agenda', $(this).data('id'), { path: '/' });
          });

          if ($.cookie('agenda-worker-tabs')) {
              $.each($.cookie('agenda-worker-tabs'), function (i, worker_selector) {
                  toggle_worker('#' + worker_selector);
              });
              if ($.cookie('active-worker-agenda'))
              {
                  var target = $('#link-tab-worker-' + $.cookie('active-worker-agenda'));
                  if (target.is(':visible')) {
                      target.click();
                  }
              }
          }
      }

      if ($('.ressource-item').length) {
          $('.ressource-item').on('click', function() {
              var target = toggle_ressource(this);
              if ($(target).is(':visible')) {
                  $(target).click();
              }
              if ($('#filtre input').val()) {
                  $('#filtre input').val('');
                  $('#filtre input').keyup();
                  $('#filtre input').focus();
              }
          });

          $('div.agenda > div').accordion({active: false, autoHeight: false});

          $('a.tab').click(function() {
              $.cookie('active-ressource-agenda', $(this).data('id'), { path: '/' });
          });

          if ($.cookie('agenda-ressource-tabs')) {
              $.each($.cookie('agenda-ressource-tabs'), function (i, ressource_selector) {
                  toggle_ressource('#' + ressource_selector);
              });
              if ($.cookie('active-ressource-agenda'))
              {
                  var target = $('#link-tab-ressource-' + $.cookie('active-ressource-agenda'));
                  if (target.is(':visible')) {
                      target.click();
                  }
              }
          }
      }

      $('a.close-tab').click(function() {
          $('#' + $(this).data('target')).click()
      });


      /* Gestion du filtre sur les utilisateurs */
      $('#filtre input').keyup(function() {
          var filtre = $(this).val();
	  if ($('#show-everybody').length) {
              var everybody = $('#show-everybody').is(':checked');
	  } else {
              var everybody = true;
          }
          if (filtre) {
              $('#show-everybody').attr('checked', true);
              $('#users li').each(function() {
                  if ($(this).text().match(new RegExp(filtre, "i"))) {
                      $(this).show();
                  } else {
                      $(this).hide();
                  }
              });
          } else {
              $('#users li').show();
              if (! everybody) {
                  $('.person-item:not(.in_service)').hide();
                  $('.person-item:not(.intervenant)').hide();
              }
          }
          /* hide worker type titles that do not have a single visible person */
          $("#users ul:has(*):has(:visible)").parent().prev().show();
          $("#users ul:has(*):not(:has(:visible))").parent().prev().hide();
      });

      $('.date').datepicker({showOn: 'button'});
      $('#add-intervenant-btn').click(function() {
          var text = $(this).prev().val();
          $('#intervenants ul').append('<li><input type="checkbox" value="' + text + '" checked="checked">' + text + '</input></li>');
          $(this).prev().val('').focus();
          return false;
      });
      enable_events($('body'));
      $('#show-everybody').change(function() {
      if (! $(this).is(':checked')) {
        $('#filtre input').val('');
      }
      $('#filtre input').keyup();
      return;
    });
    $('select[name^="act_state"]').on('change', function () {
    $(this).next('button').prop('disabled',
      ($(this).data('previous') == $(this).val()));
    })
    $('#filtre input').keyup();
  });
})(window.jQuery)
