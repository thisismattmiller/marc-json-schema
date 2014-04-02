
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
from os import listdir
from os.path import isfile, join
import requests,sys, string, json

class marcDoc2Json:



	dataDirectory = "marcDocs/"
	dataDirectoryFixed = "marcDocs/fixed/"
	schema = {}


	def __init__(self):


		#self.downloadHTML()

		self.files = [ f for f in listdir(self.dataDirectoryFixed) if isfile(join(self.dataDirectoryFixed,f)) ]

		for f in self.files:
			print ("Processing", f)
			self.processing = f
			with open(self.dataDirectoryFixed + f, encoding='utf-8') as aFile:
				html = aFile.read()			
			self.processHTMLFixed(html)


		self.files = [ f for f in listdir(self.dataDirectory) if isfile(join(self.dataDirectory,f)) ]

		for f in self.files:

			print ("Processing", f)
			with open(self.dataDirectory + f, encoding='utf-8') as aFile:
				html = aFile.read()
			
			self.processHTML(html)

		with open("../marc21_biblo_schema.json",'w') as aFile:
			aFile.write(json.dumps(self.schema, sort_keys=True, indent=4, separators=(',', ': ')))		



		



	def downloadHTML(self):

		baseURL = "http://www.loc.gov/marc/bibliographic/bd{CODE}.html"

		for x in range(10,1000):

			url = baseURL.replace("{CODE}","%03d" % (x,))
			r = requests.get(url)
			if r.status_code == 200:
				with open(dataDirectory+"%03d" % (x,), 'w') as newfile:
					 newfile.write(r.text)
				print ("%03d" % (x,), " - Good")
			else:
				print ("%03d" % (x,), " - Bad")


		#download the fixed field stuff
		codes = ['leader', '001','003','005','006','007a','007c','007d','007f','007g','007h','007k','007m','007o','007q','007r','007s','007t','007v','007z', '008a', '008b', '008c', '008p', '008m', '008s', '008v', '008x']
		for x in codes:

			url = baseURL.replace("{CODE}",x)
			r = requests.get(url)
			if r.status_code == 200:
				with open(dataDirectoryFixed+x, 'w') as newfile:
					 newfile.write(r.text)
				print (x, " - Good")
			else:
				print (x, " - Bad")



	def processHTMLFixed(self, html):


		extraSpecialFields = ['007','008']
		
		soup = BeautifulSoup(html)
		tables = soup.find_all("table")

		fieldName = soup('h1')
		foundFieldName = True



		if len(fieldName) > 0:
			fieldName=fieldName[0].text
			if fieldName.find(" - ")>-1:
				fieldNumber = fieldName.split(" - ")[0].strip()
				fieldTitle = fieldName.split(" - ")[1].strip()

				if fieldTitle.find("(NR)") > -1:
					fieldRepeatable = False
				else:
					fieldRepeatable = True
				fieldTitle = fieldTitle.replace("(NR)","").replace("(R)","").strip()
			else:				
				if (fieldName.find("(NR)") > -1 or fieldName.find("(R)") > -1):
					#... its the leader field
					fieldNumber = fieldName[0:3]
					fieldTitle = fieldName.strip()
					if fieldTitle.find("(NR)") > -1:
						fieldRepeatable = False
					else:
						fieldRepeatable = True
					fieldTitle = fieldTitle.replace("(NR)","").replace("(R)","").strip()
				else:

					foundFieldName = False
		else:
			foundFieldName = False


		allPositions = []

		#one layout they do
		if len(soup.find_all('td', {'class': 'characterPositionTitle'})) > 0:

			aPosition = {}

			for x in soup.find_all('td', {'colspan': '2'}):


				position = x.text

				pos, name = position.strip().split(' - ')

				if pos.find("-") > -1:
					start, stop = pos.split('-')
				else:
					start = stop =  pos


				if not start.isdigit or not stop.isdigit:

					print ("Error, the positions are not numeric", x.text)


				aPosition["name"] = name
				aPosition["start"] = int(start)
				aPosition["stop"] = int(stop)
				aPosition["values"] = {}


				value = ""
				for item in x.parent.next_siblings:
					value = ' '.join(str(item).split()) 
					if (value.strip().lstrip()!=''):
						break

				if value == "":
					print ("Error, could not find position values", x.text)

				else:

					for dd in BeautifulSoup(str(value)).find_all("dd"):

						postionValue = dd.text

						if postionValue.find(" - ") == -1:
							print("Error, postion is not parseable",postionValue)

						code, name = postionValue.split(" - ") 


						aPosition["values"][code] = name

				allPositions.append(aPosition.copy())


		#pretty sick of this..
		if len(allPositions) == 0 and self.processing != '006':

			if len(soup.find_all('td', {'width': '45%'})) > 1:

				activeCat = ""
				groups = {}
				for td in soup.find_all('td', {'width': '45%'}):
					lines = str(td).replace("</br>",'').replace("<br/>",'').replace("\n",'').replace("\t",'').replace("</td>",'').replace('<td width="45%">','').split("<br>")
					
					

					for line in lines:

						line = ' '.join(line.split()) 						

						if line.find("</strong>") > -1 and line.find(" - ") > -1:
							line = line.replace("</strong>",'').replace("<strong>",'')							
							

							pos, name = line.strip().split(' - ')
							if pos.find("-") > -1:
								start, stop = pos.split('-')
							else:
								start = stop =  pos

							if not start.isdigit or not stop.isdigit:
								print ("Error, the positions are not numeric", line)

							activeCat = name

							groups[activeCat] = ({"name": name, "start": int(start), "stop": int(stop), "values" : {} })		



						elif line.find(" - ") > -1:

							#print (line,activeCat)
							code, value = line.split(" - ") 

							groups[activeCat]['values'][code] = value 

					
					for x in groups:
						allPositions.append(groups[x])


		if len(allPositions) == 0 and self.processing != '001' and self.processing != '003' and self.processing != '005':


			allPositions = {}

			titleMap006 = {
				"Books" : "008b",
				"Computer files/Electronic resources" : "008c",
				"Music" : "008m",
				"Continuing resources" : "008s",
				"Visual materials" : "008v",
				"Maps" : "008p",
				"Mixed materials" : "008x"
			}


			if len(soup.find_all('td', {'width': '45%'})) > 1:

				for td in soup.find_all('td', {'width': '45%'}):
					lines = str(td).replace("</br>",'').replace("<br/>",'').replace("\n",'').replace("\t",'').replace("</td>",'').split("<br>")
					activeCat = ""
					groups = {}

					for line in lines:

						line = ' '.join(line.split()) 

						if line.find("</em>") > -1:
							line = line.replace("</em>",'').replace("<em>",'')							
							activeCat = titleMap006[line]
							
							groups[activeCat] = []			

						if line.find(" - ") > -1:
							pos, name = line.strip().split(' - ')
							if pos.find("-") > -1:
								start, stop = pos.split('-')
							else:
								start = stop =  pos

							if not start.isdigit or not stop.isdigit:
								print ("Error, the positions are not numeric", line)
							if activeCat != '':
								groups[activeCat].append({"name": name, "start": int(start), "stop": int(stop)})

					if activeCat != "":
						
						for x in groups:
							allPositions[x] =groups[x].copy()
							print (x)
						
						#allPositions = groups.copy()



		print (fieldNumber, fieldTitle)

		if fieldNumber == "008" or fieldNumber == "007" or fieldNumber == 'Lea':
			fieldNumber = self.processing


		self.schema[fieldNumber] = { "repeatable" :  fieldRepeatable, "name" : fieldTitle, "fixed" : True, "positions" : allPositions}



	def processHTML(self, html):



		soup = BeautifulSoup(html)

		tables = soup.find_all("table")



		fieldName = soup('h1')
		foundFieldName = True

		if len(fieldName) > 0:
			fieldName=fieldName[0].text
			if fieldName.find(" - ")>-1:
				fieldNumber = fieldName.split(" - ")[0].strip()
				fieldTitle = fieldName.split(" - ")[1].strip()

				if fieldTitle.find("(NR)") > -1:
					fieldRepeatable = False
				else:
					fieldRepeatable = True

				fieldTitle = fieldTitle.replace("(NR)","").replace("(R)","").strip()



			else:
				foundFieldName = False

		else:
			foundFieldName = False




		#the indicators
		foundIndicators = True

		indicators = soup('td',{'width':'45%'})
		if len(indicators) > 1:
			if indicators[0].contents[0].text.strip() == "First Indicator" and indicators[1].contents[0].text.strip() == "Second Indicator":
				indicators = [indicators[0], indicators[1]]
				bothIndicators = self.processIndicators(indicators)
			else:
				foundIndicators = False
		else:
			foundIndicators = False










		#maybe it is their alternate html layout 

		if not foundIndicators:
			foundIndicators = True
			indicators = soup('table',{'class':'indicators'})
			if len(indicators) == 1:
				subSoup = BeautifulSoup(str(indicators))
				indicators = [subSoup.find_all("td")[0], subSoup.find_all("td")[1]]
				bothIndicators = self.processIndicators(indicators)
			else:
				foundIndicators = False


		#maybe its their other alternative html layout :(
		if not foundIndicators:
			indicators = soup('td',{'width': ['42%', '58%']})
			foundIndicators = True
			if len(indicators) > 1:
				if indicators[0].contents[0].text.strip() == "First Indicator" and indicators[1].contents[0].text.strip() == "Second Indicator":
					indicators = [indicators[0], indicators[1]]
					bothIndicators = self.processIndicators(indicators)
				else:
					foundIndicators = False
			else:
				foundIndicators = False






		#subfields
		foundSubfields = True

		subfields = soup('td',{'colspan':'1'})

		foundFields = {}
		lastCode = ""

		if len(subfields) > 1:

			subfields = subfields[:2]


			for aSubfield in subfields:


				aSubfield = str(aSubfield).replace('<td colspan="1">','').replace('</td>','').replace('</br>','').replace("<br/>","").replace("\n",'').replace("\t",'').replace("&nbsp;",'').replace("<em>",'').replace("</em>",'')

				aSubfield = ' '.join(aSubfield.split())
				fields = aSubfield.split("<br>")
				

				for f in fields:

					aField = {}

					f = f.strip()

					if f.find("$") > -1 and f.find(" - ") > -1:
						code, desc = f.split(" - ")
						code = code.replace("$","")

						if desc.find("(NR)") > -1:
							repeatable = False
						else:
							repeatable = True

						desc = desc.replace("(NR)","").replace("(R)","").replace("</br>","").replace("<br/>","").replace("\n",'').replace("\t",'').replace("&nbsp;",'').strip()
						foundFields[code]  = { "name" : desc, "repeatable" : repeatable, "static": False}
						lastCode = code

					else:


						#this means that there were field values for this subfield 
						if f.find(" - ") > -1:
							
							if "staticValues" not in foundFields[lastCode]:
								foundFields[lastCode]['staticValues'] = {}

							foundFields[lastCode]['static'] = True
							code, desc = f.split(" - ")
							code=code.replace("/",'')

							foundFields[lastCode]['staticValues'][code] = {"name": desc, "value":code}






			#print (foundFields)

		else:

			foundSubfields = False





		#they have an entirely diffrent subfield layout using lists so process that one as well if no subfields found
		if not foundSubfields:


			foundSubfields = True

			subfields = soup('ul',{'class':'nomark'})

			foundFields = {}
			lastCode = ""

			if len(subfields) > 0:
				
				subSoup = BeautifulSoup(str(subfields))
				subfields = subSoup.find_all("li")

				for f in subfields:

					aField = {}

					f = str(f).strip().replace("<span>",'').replace("</span>",'').replace("<li>",'').replace("</li>",'').replace('<li class="changed">','').replace("\n",'').replace("\t",'').replace("&nbsp;",'')
					f = ' '.join(f.split())

					orgF = f
					f = f.split("<br/>")[0]

					if f.find("$") > -1 and f.find(" - ") > -1:

						if len(f.split(" - ")) > 2:
							code = f.split(" - ")[0]
							desc = " ".join(f.split(" - ")[1:])
						else:
							code, desc = f.split(" - ")

						code = code.replace("$","")

						if desc.find("(NR)") > -1:
							repeatable = False
						else:
							repeatable = True

						desc = desc.replace("(NR)","").replace("(R)","").replace("</br>","").replace("<br/>","").replace("\n",'').replace("\t",'').replace("&nbsp;",'').strip()
						foundFields[code]  = { "name" : desc, "repeatable" : repeatable, "static": False}
						lastCode = code

					else:
						print ("Static values for the alt layout!!!!")


					if len(orgF.split("<br/>")) > 1:

						f = orgF.split("<br/>")[1:]
						for ff in f:
							ff = ff.encode("ascii", 'ignore')
							ff = ff.decode("utf-8")
							ff = ' '.join(ff.split())
							ff = ff.strip().replace("/",'')
							if ff.find(" - ") > -1:

								code, desc = ff.split(" - ")
								code = code.replace(" ","")

								if "staticValues" not in foundFields[lastCode]:
									foundFields[lastCode]['staticValues'] = {}

								foundFields[lastCode]['static'] = True
								foundFields[lastCode]['staticValues'][code] = {"name": desc, "value":code}

			else:

				foundSubfields = False



		if not foundFieldName: 
			print ("Could not find field title!")
			sys.exit()



		if not foundIndicators: 
			print (fieldNumber, fieldTitle, "Has no idicators")
			

		if not foundSubfields: 
			print (fieldNumber, fieldTitle, "Has no subfields")
		else:
			

			for f in foundFields.copy():

				if len(f) != 1:

					#some fields uses a range notation to list a range of possiblities, both alpha and numeric
					if f.find("-")>-1:
						start, stop = f.split('-')
						if start.isdigit() and stop.isdigit():
							start = int(start)
							stop = int(stop)
							aRange = range(start,stop+1)

							#now delete the orginal but store its properties
							
							r = foundFields[f]['repeatable']
							s = foundFields[f]['static']
							n = foundFields[f]['name']

							for x in aRange:
								foundFields[str(x)] = { "repeatable" : r, "static" : s, "name" : n  }

							#now delete the orginal
							foundFields.pop(f,None)
							


						elif not start.isdigit() and not stop.isdigit():

							start, stop = f.split('-')

							letters = list(string.ascii_lowercase)

							start = letters.index(start) + 97
							stop = letters.index(stop) + 97
							aRange = range(start,stop+1)
							r = foundFields[f]['repeatable']
							s = foundFields[f]['static']
							n = foundFields[f]['name']

							for x in aRange:
								foundFields[ chr(x) ] = { "repeatable" : r, "static" : s, "name" : n  }
							
							#now delete the orginal
							foundFields.pop(f,None)




		self.schema[fieldNumber] = { "repeatable" :  fieldRepeatable, "name" : fieldTitle, "indicators" : bothIndicators, "subfields" :  foundFields , "fixed" : False }

	def processIndicators(self,indicators):

		bothIndicators = {}

		count =1 

		for aIndicator in indicators:


			indicatorContents = str(aIndicator.contents[1])

			indicatorContents = indicatorContents.split("<br>")
			indicatorContents = indicatorContents[1:]

			if len(indicatorContents) == 0:

				indicatorContents = str(aIndicator)
				indicatorContents = indicatorContents.replace('<td>','').replace('</td>','').replace('<span>','').replace('</span>','').split("<br/>")


			if indicatorContents[0].strip()[0:4] == "<em>":
				indicatorContentsTitle = indicatorContents[0].strip().replace("<em>",'').replace("</em>",'').strip()
			else:
				foundIndicators = False

			indicatorContents = indicatorContents[1:]

			indicatorContentsValues = {}

			for x in indicatorContents:
				if x.find("</br>") > -1:
					continue

				if x.find(" - ") > -1:
					indicatorContentsValues[x.split(" - ")[0].strip()] = x.split(" - ")[1].strip().replace("<em>",'').replace("</em>",'')

			bothIndicators[count] = {'name' : indicatorContentsTitle, 'values': indicatorContentsValues}

		
			count+=1

		return bothIndicators


if __name__ == "__main__":

	s = marcDoc2Json()
