<!DOCTYPE HTML>
<html>
<head>
<%
    from notifserver import VERSION
    from notifserver.storage import new_token
    import hashlib
    import urllib
    import time

    response = pageargs.get('response')
    username = response.get('username')
    gravatar = "http://www.gravatar.com/avatar/%s?s=%s&d=%s" % \
         (hashlib.md5(username).hexdigest().lower(),
            100,
            urllib.quote('http://push1.mtv1.dev.svc.mozilla.com/s/default.jpg'))
    user_info = response.get('user_info')
    auth = response.get('auth')
    queues = response.get('subscriptions')
    if len(queues) == 0:
        queues = None
    
    newtoken = new_token()

%>
<link rel="stylesheet" type="text/css" href="/s/style.css" />
<meta name="page" content="user" />
</head>
<body>
<header>
<img src="${gravatar}" width=100>
<h1>${username|h}</h1>
</header>
<main>
%if queues is not None:
%for queue in queues.values():
 <div id="${queue.get('queue_id')}" class="subs">
  <div class="email"><a href="mailto:${queue.get('queue_id')}@push1.mtv1.dev.svc.mozilla.com">${queue.get('queue_id')}@push1.mtv1.dev.svc.mozilla.com</a></div>
  <div class="info">
   <div class="site"><b>Site:</b> ${queue.get('origin')}</div>
   <div class="status"><b>Status:</b> ${queue.get('state')}</div>
   <div class="created"><b>Created:</b> ${time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(float(queue.get('created'))))}</div>
  </div>
  <div class="actions">
   <button class="delete" value="${queue.get('queue_id')}">Delete</button>
  </div>
 </div>
%endfor
</table>
%else:
<h2>No queues found</h2>
%endif
<p>
<form id="newsub" method="post" action="/${VERSION}/new_subscription">
<input name="token" type="hidden" value = "${newtoken}">
<input name="origin" value = "example.com">
<button type="submit" >Add Subs.</button>
</form>
</main>
<footer>
<a class="fakebutton" href="/logout">Logout</a>
</footer>
<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.6.4/jquery.min.js" type="text/javascript"></script>
<script type="application/javascript">
$(function() {
    $('.delete').click(function(event) {
            queue_id = this.value;
            console.debug('calling /${VERSION}/remove_subscription');
            $.ajax({url: '/${VERSION}/remove_subscription',
                    data: JSON.stringify({token: queue_id}),
                    type: 'POST',
                    contentType: 'application/javascript',
                    success: function (data, status, xhr) {
                        $('#' + queue_id).detach();
                        console.debug('success!');
                    },
                    error: function (xhr, status, error) {
                        console.debug('error:');
                        console.debug(status);
                        console.debug(error);
                    }
                });
        })
    $('#newsub').submit(function(event) {
            data ={}
            $('#newsub input').each(function(index, element) {
                data[element.name] = element.value 
                });
            console.debug(JSON.stringify(data));
            $.ajax({url: '/${VERSION}/new_subscription',
                contentType: 'application/javascript',
                data: JSON.stringify(data),
                type: 'POST',
                success: function (data, status, xhr) {
                    document.location = "/";
                },
                error: function (xhr, status, error) {
                    console.error('error: ' + status + error);
                }
            });
            return false;
        })
    })
</script>
</body>
</html>
