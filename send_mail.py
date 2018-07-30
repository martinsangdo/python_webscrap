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
msg['Subject'] = "Your newsletter in this week"
msg['From'] = me
msg['To'] = you

# Create the body of the message (a plain-text and an HTML version).
html = """\
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
<head>
<!-- If you delete this meta tag, the ground will open and swallow you. -->
<meta name="viewport" content="width=device-width" />

<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<title>Blockbod Newsletter</title>

<link rel="stylesheet" type="text/css" href="http://blockbod.com/public/blockbod/css/email.css"/>

</head>

<body bgcolor="#FFFFFF" topmargin="0" leftmargin="0" marginheight="0" marginwidth="0">

<!-- HEADER -->
<table class="head-wrap">
	<tr>
		<td></td>
		<td class="header container">
			<!-- /content -->
			<div class="content">
				<table>
					<tr>
						<td width="5%"><img src="http://blockbod.com/public/blockbod/img/logo.png" style="width:50px;height:auto;"/></td>
            <td style="font-weight:bold;">BLOCKBOD NEWSLETTER</td>
					</tr>
				</table>
			</div><!-- /content -->

		</td>
		<td></td>
	</tr>
</table><!-- /HEADER -->
<hr/>
<!-- BODY -->
<table class="body-wrap">
	<tr>
		<td></td>
		<td class="container" bgcolor="#fff">
			<!-- content -->
			<div class="content">
				<table>
					<tr>
						<td>
							<p class="lead">Dear customer, we would like to send relavant news of this week based on your custom request. Enjoy it!</p>
							<!-- A Real Hero (and a real human being) -->
							<p><a href="http://blockbod.com/blockchain-news/french-tennis-athlete-monfils-signs-sponsorship-deal-etoro"><img src="https://btcmanager.com/wp-content/uploads/2018/07/Tennis-Player-Monfils-Signs-Up-Trading-Platform-eToro-As-A-Sponsor-768x458.jpg" style="width:600px;height:auto;"/></a></p>
              <h5><a href="http://blockbod.com/blockchain-news/french-tennis-athlete-monfils-signs-sponsorship-deal-etoro">French Tennis Player Monfils Signs Sponsorship Deal with eToro</a></h5>
							<p>Popular trading platform eToro has announced a partnership with renowned tennis player Monfils. Nicknamed "Sliderman," Monfils was ranked number six in the world after his successful tournament run in 2016. An avid cryptocurrency trader, Monfils decided to sign a sponsorship agreement with the company after using it for his personal financial management.</p>
						</td>
					</tr>
				</table>
			</div><!-- /content -->

			<!-- content -->
			<div class="content">
				<table>
					<tr>
						<td class="small" width="15%" style="vertical-align: top; padding-right:5px;">
              <a href="http://blockbod.com/blockchain-news/us-government-backs-dlt-based-energy-grid-with-1-million-grant"><img src="https://media.coindesk.com/uploads/2018/07/electric-grid-768x512.jpg" style="width:75px;height:75px;"/></a>
            </td>
						<td>
							<h6><a href="http://blockbod.com/blockchain-news/us-government-backs-dlt-based-energy-grid-with-1-million-grant">US Government Backs DLT-Based Energy Grid With $1 Million Grant</a></h6>
							<p>The U.S. Department of Energy (DoE) has announced it will award a grant of nearly $1 million to a blockchain startup in an effort to advance the development of a decentralized energy grid infrastructure.</p>
						</td>
					</tr>
				</table>
			</div><!-- /content -->

			<!-- content -->
			<div class="content">
				<table>
					<tr>
						<td>
							<!-- social & contact -->
							<table bgcolor="" class="social" width="100%">
								<tr>
									<td>

										<!--- column 1 -->
										<div class="column">
											<table bgcolor="" cellpadding="" align="left">
										<tr>
											<td>

												<h5 class="">Connect with Us:</h5>
												<p class=""><a href="#" class="soc-btn fb">Facebook</a> <a href="#" class="soc-btn tw">Twitter</a> <a href="#" class="soc-btn gp">Google+</a></p>


											</td>
										</tr>
									</table><!-- /column 1 -->
										</div>

										<!--- column 2 -->
										<div class="column">
											<table bgcolor="" cellpadding="" align="left">
										<tr>
											<td>

												<h5 class="">Contact Info:</h5>
												<p>Phone: <strong>408.341.0600</strong><br/>
                Email: <strong><a href="emailto:hseldon@trantor.com">hseldon@trantor.com</a></strong></p>

											</td>
										</tr>
									</table><!-- /column 2 -->
										</div>

										<div class="clear"></div>

									</td>
								</tr>
							</table><!-- /social & contact -->

						</td>
					</tr>
				</table>
			</div><!-- /content -->


		</td>
		<td></td>
	</tr>
</table><!-- /BODY -->

<!-- FOOTER -->
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
									<a href="#">Terms</a> |
									<a href="#">Privacy</a> |
									<a href="#"><unsubscribe>Unsubscribe</unsubscribe></a>
								</p>
							</td>
						</tr>
					</table>
				</div><!-- /content -->

		</td>
		<td></td>
	</tr>
</table><!-- /FOOTER -->

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
s.login('payment@blockbod.com', 'Block!234')
# sendmail function takes 3 arguments: sender's address, recipient's address
# and message to send - here it is sent as one string.
s.sendmail(me, you, msg.as_string())
s.quit()
