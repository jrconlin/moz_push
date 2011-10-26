<!DOCTYPE HTML>
<html>
<head>
<%
    from notifserver import VERSION

    postback = pageargs.get('postback','/')
    audience = pageargs.get('audience','UNKNOWN')
%>
 <link rel="stylesheet" type="text/css" href="/s/style.css" />
<meta name="page" content="index" />
</head>
<body>
<header>
<h1>Please Log In</h1>
</header>
<main>
<div id="browserid"><img src="https://browserid.org/i/sign_in_grey.png" id="signin"/></div>

</main>
<footer>
</footer>
<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.6.4/jquery.min.js" type="text/javascript"></script>
<script src="http://browserid.org/include.js" type="text/javascript"></script>
<script type="text/javascript">
$(function() {
    $('#signin').click(function(){
        navigator.id.getVerifiedEmail(function(assertion) {
            if (assertion) {
                var $form = $("<form metthod='POST' action='${postback}'>" +
                "<input type='hidden' name='password' value='" + assertion +
                "' /><input type='hidden' name='username' value='${audience}'>"+
                "</form>").appendTo('#browserid');
            $form.submit();
            }
        })
    });
    $('#signin').attr('src',"https://browserid.org/i/sign_in_blue.png");
})
</script>
</body>
</html>
