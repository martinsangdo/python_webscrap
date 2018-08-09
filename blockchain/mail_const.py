#constant for sending mail
PER_PAGE=10
SMTP_HOSTNAME = 'smtp.1and1.com'
SMTP_POST=25

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
						<td width="5%"><img src="http://blockbod.com/public/blockbod/img/logo.png" style="width:50px;height:auto;"/></td>
            			<td style="font-weight:bold;">BLOCKBOD NEWSLETTER</td>
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
		<td class="container" bgcolor="#fff">
"""
CUSTOM_NEWS_HTML_SMALL_ITEM_TMPL = """\
			<div class="content">
				<table>
					<tr>
						<td class="small" width="15%" style="vertical-align: top; padding-right:5px;">
			              <a href="%slug_url%"><img src="%thumb_url%" style="width:75px;height:75px;"/></a>
			            </td>
						<td>
							<h6><a href="%slug_url%">%title%</a></h6>
							%excerpt%
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
