import {
	type IExecuteFunctions,
	type ILoadOptionsFunctions,
	type INodeExecutionData,
	type INodePropertyOptions,
	type INodeType,
	type INodeTypeDescription,
} from 'n8n-workflow';

export class SleeperApiNode implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'Sleeper API',
		name: 'sleeperApi',
		icon: 'file:sleeper_logo.svg',
		group: ['transform'],
		version: 1,
		subtitle: '={{$parameter["operation"] + ": " + $parameter["resource"]}}',
		description: 'Interact with Sleeper Fantasy Football API',
		defaults: {
			name: 'Sleeper API',
		},
		inputs: [],
		outputs: [],
		credentials: [
			{
				name: 'sleeperCredential',
				required: true,
			},
		],
		properties: [
			{
				displayName: 'Resource Type',
				name: 'resource',
				type: 'options',
				noDataExpression: true,
				options: [
					{
						name: 'User',
						value: 'user',
					},
					{
						name: 'League',
						value: 'league',
					},
					{
						name: 'Draft',
						value: 'draft',
					},
					{
						name: 'Players',
						value: 'players',
					},
				],
				default: 'user',
			},

			// User Operations
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: {
					show: {
						resource: ['user'],
					},
				},
				options: [
					{
						name: 'Get My Profile',
						value: 'getUser',
						description: 'Get your Sleeper profile information',
						action: 'Get my profile',
					},
				],
				default: 'getUser',
			},

			// League Operations
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: {
					show: {
						resource: ['league'],
					},
				},
				options: [
					{
						name: 'Get Rosters',
						value: 'getRosters',
						description: 'Get all rosters in your league',
						action: 'Get league rosters',
					},
					{
						name: 'Get Matchups',
						value: 'getMatchups',
						description: 'Get matchups for a specific week',
						action: 'Get weekly matchups',
					},
					{
						name: 'Get Transactions',
						value: 'getTransactions',
						description: 'Get transactions for a specific week',
						action: 'Get league transactions',
					},
				],
				default: 'getRosters',
			},
			{
				displayName: 'League',
				name: 'leagueId',
				type: 'options',
				typeOptions: {
					loadOptionsMethod: 'getLeagues',
				},
				required: true,
				displayOptions: {
					show: {
						resource: ['league'],
					},
				},
				default: '',
				description: 'Select one of your leagues',
			},
			{
				displayName: 'Season',
				name: 'season',
				type: 'number',
				required: true,
				displayOptions: {
					show: {
						resource: ['league'],
					},
				},
				default: 2025,
				description: 'NFL season year',
			},
			{
				displayName: 'Week',
				name: 'week',
				type: 'number',
				required: true,
				displayOptions: {
					show: {
						resource: ['league'],
						operation: ['getMatchups', 'getTransactions'],
					},
				},
				default: 1,
				description: 'Week number (1-18)',
			},

			// Draft Operations
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: {
					show: {
						resource: ['draft'],
					},
				},
				options: [
					{
						name: 'Get Draft Details',
						value: 'getDraft',
						description: 'Get draft settings and metadata',
						action: 'Get draft details',
					},
					{
						name: 'Get Draft Picks',
						value: 'getDraftPicks',
						description: 'Get all picks made in the draft',
						action: 'Get all draft picks',
					},
					{
						name: 'Get Traded Picks',
						value: 'getTradedPicks',
						description: 'Get draft picks that were traded',
						action: 'Get traded draft picks',
					},
				],
				default: 'getDraft',
			},
			{
				displayName: 'League',
				name: 'leagueId',
				type: 'options',
				typeOptions: {
					loadOptionsMethod: 'getLeagues',
				},
				required: true,
				displayOptions: {
					show: {
						resource: ['draft'],
					},
				},
				default: '',
				description: 'Select one of your leagues',
			},
			{
				displayName: 'Season',
				name: 'season',
				type: 'number',
				required: true,
				displayOptions: {
					show: {
						resource: ['draft'],
					},
				},
				default: 2025,
				description: 'NFL season year',
			},
			{
				displayName: 'Draft',
				name: 'draftId',
				type: 'options',
				typeOptions: {
					loadOptionsMethod: 'getDrafts',
					loadOptionsDependsOn: ['leagueId'],
				},
				required: true,
				displayOptions: {
					show: {
						resource: ['draft'],
					},
				},
				default: '',
				description: 'Select a draft from the league',
			},

			// Players Operations
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: {
					show: {
						resource: ['players'],
					},
				},
				options: [
					{
						name: 'Get All Players',
						value: 'getAllPlayers',
						description: 'Get all NFL players (~5MB)',
						action: 'Get all NFL players',
					},
					{
						name: 'Get NFL State',
						value: 'getNflState',
						description: 'Get current NFL season/week',
						action: 'Get current NFL season and week',
					},
				],
				default: 'getAllPlayers',
			},
		],
	};

	methods = {
		loadOptions: {
			async getLeagues(this: ILoadOptionsFunctions): Promise<INodePropertyOptions[]> {
				const credentials = await this.getCredentials('sleeperCredential');
				const username = credentials.username as string;
				const season = this.getNodeParameter('season', 0) as number;
				const baseUrl = 'https://api.sleeper.app/v1';

				try {
					// First get user ID from username
					const userResponse = await this.helpers.httpRequest({
						method: 'GET',
						url: `${baseUrl}/user/${username}`,
						json: true,
					});

					const userId = userResponse.user_id;

					// Then get user's leagues
					const leaguesResponse = await this.helpers.httpRequest({
						method: 'GET',
						url: `${baseUrl}/user/${userId}/leagues/nfl/${season}`,
						json: true,
					});

					return leaguesResponse.map((league: any) => ({
						name: league.name,
						value: league.league_id,
						description: `${league.total_rosters} teams • ${league.settings.type || 'Redraft'}`,
					}));
				} catch (error) {
					return [];
				}
			},

			async getDrafts(this: ILoadOptionsFunctions): Promise<INodePropertyOptions[]> {
				const leagueId = this.getNodeParameter('leagueId', 0) as string;
				const baseUrl = 'https://api.sleeper.app/v1';

				try {
					// Get league details to find draft IDs
					const leagueResponse = await this.helpers.httpRequest({
						method: 'GET',
						url: `${baseUrl}/league/${leagueId}`,
						json: true,
					});

					const drafts: INodePropertyOptions[] = [];

					// Add current draft if exists
					if (leagueResponse.draft_id) {
						const draftResponse = await this.helpers.httpRequest({
							method: 'GET',
							url: `${baseUrl}/draft/${leagueResponse.draft_id}`,
							json: true,
						});

						drafts.push({
							name: `${draftResponse.type || 'Draft'} (${draftResponse.status})`,
							value: leagueResponse.draft_id,
							description: `${draftResponse.settings?.rounds || 'Unknown'} rounds`,
						});
					}

					// Add previous season drafts if available
					if (leagueResponse.previous_league_id) {
						const prevLeagueResponse = await this.helpers.httpRequest({
							method: 'GET',
							url: `${baseUrl}/league/${leagueResponse.previous_league_id}`,
							json: true,
						});

						if (prevLeagueResponse.draft_id) {
							const prevDraftResponse = await this.helpers.httpRequest({
								method: 'GET',
								url: `${baseUrl}/draft/${prevLeagueResponse.draft_id}`,
								json: true,
							});

							drafts.push({
								name: `Previous Season Draft (${prevDraftResponse.status})`,
								value: prevLeagueResponse.draft_id,
								description: `${prevDraftResponse.season} season`,
							});
						}
					}

					return drafts.length > 0 ? drafts : [{ name: 'No drafts found', value: '', description: 'This league has no associated drafts' }];
				} catch (error) {
					return [];
				}
			},
		},
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const returnData: INodeExecutionData[] = [];
		const baseUrl = 'https://api.sleeper.app/v1';

		// Get credentials once (same for all items)
		const credentials = await this.getCredentials('sleeperCredential');
		const username = credentials.username as string;

		// Get user ID from username (cached for batch processing)
		let userId: string | null = null;

		for (let i = 0; i < items.length; i++) {
			try {
				const resource = this.getNodeParameter('resource', i) as string;
				const operation = this.getNodeParameter('operation', i) as string;

				let endpoint = '';
				let method = 'GET';
				let responseData;

				// Fetch user ID if needed (only once)
				if (!userId && resource !== 'players') {
					const userResponse = await this.helpers.httpRequest({
						method: 'GET',
						url: `${baseUrl}/user/${username}`,
						json: true,
					});
					userId = userResponse.user_id;
				}

				// User Operations
				if (resource === 'user') {
					if (operation === 'getUser') {
						endpoint = `/user/${username}`;
					}
				}

				// League Operations
				else if (resource === 'league') {
					const leagueId = this.getNodeParameter('leagueId', i) as string;

					if (operation === 'getRosters') {
						endpoint = `/league/${leagueId}/rosters`;
					} else if (operation === 'getMatchups') {
						const week = this.getNodeParameter('week', i) as number;
						endpoint = `/league/${leagueId}/matchups/${week}`;
					} else if (operation === 'getTransactions') {
						const week = this.getNodeParameter('week', i) as number;
						endpoint = `/league/${leagueId}/transactions/${week}`;
					}
				}

				// Draft Operations
				else if (resource === 'draft') {
					const draftId = this.getNodeParameter('draftId', i) as string;

					if (operation === 'getDraft') {
						endpoint = `/draft/${draftId}`;
					} else if (operation === 'getDraftPicks') {
						endpoint = `/draft/${draftId}/picks`;
					} else if (operation === 'getTradedPicks') {
						endpoint = `/draft/${draftId}/traded_picks`;
					}
				}

				// Players Operations
				else if (resource === 'players') {
					if (operation === 'getAllPlayers') {
						endpoint = '/players/nfl';
					} else if (operation === 'getNflState') {
						endpoint = '/state/nfl';
					}
				}

				// Make API request
				const options: any = {
					method,
					url: `${baseUrl}${endpoint}`,
					headers: {
						'Content-Type': 'application/json',
						'User-Agent': 'n8n-sleeper-agent/1.0',
					},
					json: true,
				};

				responseData = await this.helpers.httpRequest(options);

				// Add metadata
				const executionData = this.helpers.constructExecutionMetaData(
					this.helpers.returnJsonArray(responseData),
					{ itemData: { item: i } },
				);

				returnData.push(...executionData);
			} catch (error: any) {
				if (this.continueOnFail()) {
					returnData.push({
						json: {
							error: error.message,
						},
						pairedItem: { item: i },
					});
					continue;
				}
				throw error;
			}
		}

		return [returnData];
	}
}
