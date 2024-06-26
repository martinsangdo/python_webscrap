#constant for sending mail
PER_PAGE=10
SMTP_HOSTNAME = 'smtp.1and1.com'
SMTP_POST=25
EMPTY_MAIL_WARNING_MAX_SEND_NUM = 3     #if number of continous sending empty mail, send warning to change request
NEWS_LINK_PREFIX = 'http://blockbod.com/blockchain-news/'
#newsletter
NEWS_MAIL_FROM='no-reply@blockbod.com'
NEWS_MAIL_FROM_NAME='Blockbod Newsletter'
NEWS_MAIL_FROM_PASSWORD='Block!234'
CUSTOM_NEWS_SUBJECT='News of the Week for Your Reference'
CUSTOM_NEWS_HTML_PREFIX = """\
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
<head>
<meta name="viewport" content="width=device-width" />
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<title>News of the Week for Your Reference</title>
<link rel="stylesheet" type="text/css" href="http://blockbod.com/public/blockbod/css/email.css"/>
</head>
<body bgcolor="#fff" topmargin="0" leftmargin="0" marginheight="0" marginwidth="0">
<table class="head-wrap">
	<tr>
		<td></td>
		<td class="header container">
			<div class="content">
				<table>
					<tr>
						<td width="5%"><img class="logo" src="http://blockbod.com/public/blockbod/img/logo.png"/></td>
            			<td><strong>BLOCKBOD NEWSLETTER</strong></td>
					</tr>
				</table>
			</div>
		</td>
		<td></td>
	</tr>
</table>
<hr/>
<table class="body-wrap">
	<tr>
		<td></td>
		<td class="container">
"""
CUSTOM_NEWS_HTML_SMALL_ITEM_TMPL = """\
			<div class="content">
				<table>
					<tr>
						<td class="small small_td" width="15%">
			              <a href="%slug_url%"><img src="%thumb_url%" style="width:75px;height:75px;"/></a>
			            </td>
						<td>
							<h6><a href="%slug_url%">%title%</a></h6>
							<div class="mail_excerpt">%excerpt%</div>
						</td>
					</tr>
				</table>
			</div>
"""
CUSTOM_NEWS_HTML_POSTFIX = """\
			<div class="content" style="background-color:#eee;">
					<p>More articles from our site: <strong><a href="http://blockbod.com">blockbod.com</a></strong></p>
					<p>Email: <strong><a href="mailto:info@blockbod.com">info@blockbod.com</a></strong></p>
			</div>
		</td>
		<td></td>
	</tr>
</table>

<table class="footer-wrap">
	<tr>
		<td></td>
		<td class="container">
				<!-- content -->
				<div class="content">
					<table>
						<tr>
							<td align="center">
								<p>
									<a href="http://blockbod.com/publicapi/terms">Terms</a> |
									<a href="http://blockbod.com/publicapi/privacy">Privacy</a>
								</p>
							</td>
						</tr>
					</table>
				</div>
		</td>
		<td></td>
	</tr>
</table>

</body>
</html>
"""
EMPTY_NEWS_MAIL = '<p>There is no relevant articles in last week.<p>'\
    '<p>In case you wanna change your custom request, please drop an email to <a href="mailto:info@blockbod.com">info@blockbod.com</a></p>'
EMPTY_WARNING_NEWS_MAIL = '<p>There is no relevant articles in recent weeks.<p>'\
    '<p>You should change the custom request, please drop an email to <a href="mailto:info@blockbod.com">info@blockbod.com</a></p>'
