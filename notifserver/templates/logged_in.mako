<!DOCTYPE HTML>
<html>
<head>
<%
    from notifserver import VERSION
    from notifserver.storage import new_token
    import time

    response = pageargs.get('response')
    username = response.get('username')
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
<h1>${username|h}</h1>
</header>
<main>
%if queues is not None:
<table>
<tr><th>Site:</th>
<th>status</th>
<th>created</th>
<th></th>
</tr>
%for queue in queues.values():
 <tr>
    <td colspan="4">${queue.get('queue_id')}@push1.mtv1.dev.svc.mozilla.com</td></tr>
 <tr>
    <td>${queue.get('origin')}</td>
    <td>${queue.get('status')}</td>
    <td>${time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(float(queue.get('created'))))}</td>
    <td><button value="${queue.get('queue_id')}">Delete</button</td>
 </tr>
%endfor
</table>
%else:
<h2>No queues found</h2>
%endif
<p>
<form method="post" action="/${VERSION}/new_subscription">
<input name="token" type="hidden" value = "${newtoken}">
<input name="auth" type="hidden" value = "${auth}">
<input name="origin" value = "example.com">
<button id="submit">Add Subs.</button>
</form>
</main>
</body>
</html>
<div class="qname">
