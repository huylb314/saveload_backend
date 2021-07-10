from django.http import HttpResponse
import json
import time
from datetime import datetime

from model import models
from api.v11 import common

userList = {
  "huylb314": "607dd570316d3700355b8c4d",
  "huylhv": "607dd73e316d3700355b8c4e",
  "quannh": "607dd74d316d3700355b8c4f",
  "hoangvm": "60828885316d3700355b8c50",
  "test1": "60c5fa61ac54ec0034c014eb",
  "test2": "60c5fa68ac54ec0034c014ec",
}
useridList = {v: k for k, v in userList.items()}

def processRequest(request):
	parsedRequest = common.parseRequest(request)

	if parsedRequest['error'] is not None:
		return parsedRequest['error']

	if parsedRequest['response'] is not None:
		return parsedRequest['response']


	clientId = parsedRequest["clientId"]
	userId = parsedRequest['userId']
	chartId = request.GET.get('chart', '')


	if request.method == 'GET':
		if chartId == '':
			return getAllUserCharts(clientId, userId)
		else:
			return getChartContent(clientId, userId, chartId)

	elif request.method == 'DELETE':
		if chartId == '':
			return common.error('Wrong chart id')
		else:
			return removeChart(clientId, userId, chartId)

	elif request.method == 'POST':
		chartName = request.POST.get('name')
		symbol = request.POST.get('symbol')
		resolution = request.POST.get('resolution')
		content = request.POST.get('content')
		
		if '|' in chartName:
			splittedName, receivedName = chartName.split('|')
			symbol = request.POST.get('symbol')
			resolution = request.POST.get('resolution')
			content = request.POST.get('content')
			sharedUserId = None
			sharedChartId = None
			if receivedName in userList:
				sharedUserId = userList[receivedName]
				if not (userId == sharedUserId):
					sharedName = useridList[userId]
					sharedChartName = "{}-{}-{}".format(splittedName, sharedName, datetime.now().strftime("%H:%M:%S"))
					sharedContent = content.replace(chartName, sharedChartName)
					sharedChartId = saveChart(clientId, sharedUserId, sharedChartName, symbol, resolution, sharedContent, [], [], True)
			if chartId == '':
				return saveChart(clientId, userId, chartName, symbol, resolution, content, [sharedUserId], [sharedChartId], False)
			else:
				return rewriteChart(clientId, userId, chartId, chartName, symbol, resolution, content, [sharedUserId], [sharedChartId])
		else:
			if chartId == '':
				return saveChart(clientId, userId, chartName, symbol, resolution, content, [], [], False)
			else:
				return rewriteChart(clientId, userId, chartId, chartName, symbol, resolution, content, [], [])

	else:
		return common.error('Wrong request')


#-----------------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------------


def getAllUserCharts(clientId, userId):
	chartsList = models.Chart.objects.defer('content').filter(ownerSource = clientId, ownerId = userId)
	result = map(lambda x : {'id': x.id, 'name': x.name, 'timestamp': time.mktime(x.lastModified.timetuple()), 'symbol': x.symbol, 'resolution': x.resolution} , chartsList)
	return common.response(json.dumps({'status': "ok", 'data': list(result)}))


def getChartContent(clientId, userId, chartId):
	try:
		chart = models.Chart.objects.get(ownerSource = clientId, ownerId = userId, id = chartId)
		result = json.dumps({'status': 'ok', 'data': { 'id': chart.id, 'name': chart.name, 'timestamp': time.mktime(chart.lastModified.timetuple()), 'content': chart.content}})
		return common.response(result)
	except:
		return common.error('Chart not found')


def removeChart(clientId, userId, chartId):
	try:
		chart = models.Chart.objects.get(ownerSource = clientId, ownerId = userId, id = chartId)
		if len(chart.sharedUserId) > 0 and len(chart.sharedChartId) > 0:
			for childUserId, childChartId in zip(chart.sharedUserId, chart.sharedChartId):
				chartChild = models.Chart.objects.get(ownerSource = clientId, ownerId = childUserId, id = childChartId)
				chartChild.delete()
		chart.delete()
		return common.response(json.dumps({'status': 'ok'}))
	except:
		return common.error('Chart not found')

def saveChart(clientId, userId, chartName, symbol, resolution, content, sharedUserId=[], sharedChartId=[], returnId=False):
	newChart = models.Chart(
		ownerSource = clientId,
		ownerId = userId,
		name = chartName,
		content = content,
		lastModified = datetime.now(),
		symbol = symbol,
		resolution = resolution,
		sharedUserId = sharedUserId, 
		sharedChartId = sharedChartId
	)

	newChart.save()
	if returnId:
		return newChart.id
	return common.response(json.dumps({'status': 'ok', 'id': newChart.id}))

def rewriteChart(clientId, userId, chartId, chartName, symbol, resolution, content, sharedUserId=[], sharedChartId=[]):
	try:
		chart = models.Chart.objects.get(ownerSource = clientId, ownerId = userId, id = chartId)
		chart.lastModified = datetime.now()
		chart.content = content
		chart.name = chartName
		chart.symbol = symbol
		chart.resolution = resolution
		chart.sharedUserId.extend(sharedUserId)
		chart.sharedChartId.extend(sharedChartId)

		chart.save()
		return common.response(json.dumps({'status': 'ok'}))
	except:
		return common.error('Chart not found')
