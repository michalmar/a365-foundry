@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Container image for the agent host.')
param containerImage string

@description('Container registry name that stores the agent host image.')
param containerRegistryName string

@description('Container registry login server that stores the agent host image.')
param registryServer string

@description('Azure AI Foundry project endpoint consumed by the host.')
param projectEndpoint string

@description('Foundry agent name to resolve at startup.')
param foundryAgent string = 'OperationsEngineering'

@description('Foundry agent version for next-gen agent_reference calls.')
param foundryAgentVersion string = ''

@description('Azure tenant id for host-to-Azure authentication.')
param azureTenant string = ''

@description('Microsoft 365 tenant id for Bot/M365 authentication.')
param m365Tenant string = ''

@description('Resource group that contains the Azure AI Foundry account.')
param foundryAccountResourceGroup string

@description('Azure AI Foundry account name that hosts the project.')
param foundryAccountName string

@description('Container Apps environment name.')
param containerAppsEnvironmentName string = 'cae-a365-foundry'

@description('Agent host container app name.')
param containerAppName string = 'ca-a365-foundry-agent'

@description('Azure Bot Service resource name.')
param botName string = 'bot-a365-foundry-agent'

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' existing = {
  name: containerRegistryName
}

module identity 'identity.bicep' = {
  name: 'identity'
  params: {
    location: location
  }
}

module containerapp 'containerapp.bicep' = {
  name: 'containerapp'
  dependsOn: [
    acrPullRoleAssignment
  ]
  params: {
    location: location
    containerAppsEnvironmentName: containerAppsEnvironmentName
    containerAppName: containerAppName
    containerImage: containerImage
    registryServer: registryServer
    projectEndpoint: projectEndpoint
    foundryAgent: foundryAgent
    foundryAgentVersion: foundryAgentVersion
    azureTenant: azureTenant
    m365Tenant: m365Tenant
    identityId: identity.outputs.identityId
    identityClientId: identity.outputs.clientId
  }
}

resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, 'id-a365-foundry-agent', 'acrpull')
  scope: containerRegistry
  properties: {
    principalId: identity.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '7f951dda-4ed3-4680-a7ca-43fe172d538d'
    )
  }
}

module foundryRbac 'foundry-rbac.bicep' = {
  name: 'foundry-rbac'
  scope: resourceGroup(foundryAccountResourceGroup)
  params: {
    foundryAccountName: foundryAccountName
    principalId: identity.outputs.principalId
  }
}

module bot 'bot.bicep' = {
  name: 'bot'
  params: {
    botName: botName
    endpoint: 'https://${containerapp.outputs.fqdn}/api/messages'
    userAssignedIdentityClientId: identity.outputs.clientId
    userAssignedIdentityResourceId: identity.outputs.identityId
    tenantId: azureTenant
  }
}

output botId string = bot.outputs.botId
output containerAppFqdn string = containerapp.outputs.fqdn
output userAssignedIdentityId string = identity.outputs.identityId
output userAssignedIdentityClientId string = identity.outputs.clientId
output userAssignedIdentityPrincipalId string = identity.outputs.principalId
