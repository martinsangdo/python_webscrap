#author: Martin sangdo
#!/usr/bin/env python

import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText




# me == my email address
# you == recipient's email address
me = "no-reply@blockbod.com"
you = "dtsang012@yahoo.com"

# Create message container - the correct MIME type is multipart/alternative.
msg = MIMEMultipart('alternative')
msg['Subject'] = "News of the Week for Your Reference"
msg['From'] = 'Blockbod Newsletter'
msg['To'] = you

# Create the body of the message (a plain-text and an HTML version).
html = """\
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

			<div class="content">
				<table>
					<tr>
						<td>
							<p><a href="http://blockbod.com/blockchain-news/french-tennis-athlete-monfils-signs-sponsorship-deal-etoro"><img src="https://btcmanager.com/wp-content/uploads/2018/07/Tennis-Player-Monfils-Signs-Up-Trading-Platform-eToro-As-A-Sponsor-768x458.jpg" style="width:600px;height:auto;"/></a></p>
              				<h5><a href="http://blockbod.com/blockchain-news/french-tennis-athlete-monfils-signs-sponsorship-deal-etoro">French Tennis Player Monfils Signs Sponsorship Deal with eToro</a></h5>
							<p>Popular trading platform eToro has announced a partnership with renowned tennis player Monfils. Nicknamed "Sliderman," Monfils was ranked number six in the world after his successful tournament run in 2016. An avid cryptocurrency trader, Monfils decided to sign a sponsorship agreement with the company after using it for his personal financial management.</p>
						</td>
					</tr>
				</table>
			</div>

			<div class="content">
				<table>
					<tr>
						<td class="small" width="15%" style="vertical-align: top; padding-right:5px;">
			              <a href="http://blockbod.me:8073/blockchain-news/antonopoulos-crypto-success-is-not-measured-by-price-but-by-adoption"><img src="https://btcmanager.com/wp-content/uploads/2018/07/Antonopoulos-Crypto-Success-is-Not-Measured-by-Adoption-or-Market-Cap-768x458.jpg" style="width:75px;height:75px;"/></a>
			            </td>
						<td>
							<h6><a href="http://blockbod.me:8073/blockchain-news/antonopoulos-crypto-success-is-not-measured-by-price-but-by-adoption">Antonopoulos: Crypto Success Is not Measured by Price, but by Adoption</a></h6>
							<p>Prominent Bitcoin and security expert, Andreas Antonopoulos, recently said in a talk presented at the University College Dublin in Ireland, that the success of crypto and blockchain can not be measured by price but must be measured by adoption.</p>
						</td>
					</tr>
				</table>
			</div>
			<!-- footer -->
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

# Record the MIME types of both parts - text/plain and text/html.
# part1 = MIMEText(text, 'plain')
part2 = MIMEText(html, 'html')

# Attach parts into message container.
# According to RFC 2046, the last part of a multipart message, in this case
# the HTML message, is best and preferred.
# msg.attach(part1)
msg.attach(part2)

# Send the message via local SMTP server.
s = smtplib.SMTP('smtp.1and1.com', 25)
s.login('no-reply@blockbod.com', 'Block!234')
# sendmail function takes 3 arguments: sender's address, recipient's address
# and message to send - here it is sent as one string.
s.sendmail(me, you, msg.as_string())
s.quit()
