#!/usr/bin/env python3
import argparse
from vertexai import agent_engines

def list_agents(filter_name=None):
    """
    List all deployed agents, optionally filtered by display name.
    
    Args:
        filter_name (str, optional): Filter agents by display name
    """
    filter_str = f'display_name="{filter_name}"' if filter_name else None
    agents = list(agent_engines.list(filter=filter_str))
    
    if not agents:
        print("No agents found.")
        return
    
    print(f"Found {len(agents)} agents:")
    for i, agent in enumerate(agents, 1):
        print(f"{i}. {agent.display_name} (ID: {agent.name})")

def get_agent_details(resource_id):
    """
    Get details for a specific agent by resource ID or fully qualified name.
    
    Args:
        resource_id (str): The resource ID or fully qualified name of the agent
    """
    try:
        agent = agent_engines.get(resource_id)
        print(f"Agent details:")
        print(f"  Name: {agent.display_name}")
        print(f"  Resource ID: {agent.name}")
        print(f"  Description: {agent.description}")
        print(f"  Create time: {agent.create_time}")
        print(f"  Update time: {agent.update_time}")
    except Exception as e:
        print(f"Error retrieving agent: {e}")

def delete_agent(resource_id):
    """
    Delete a specific agent by resource ID or fully qualified name.
    
    Args:
        resource_id (str): The resource ID or fully qualified name of the agent
    """
    try:
        agent = agent_engines.get(resource_id)
        print(f"Deleting agent: {agent.display_name} (ID: {agent.name})")
        agent.delete()
        print("Agent deleted successfully.")
    except Exception as e:
        print(f"Error deleting agent: {e}")

def delete_all_agents():
    """
    Delete all deployed agents in the current project and location.
    """
    agents = list(agent_engines.list())
    
    if not agents:
        print("No agents found to delete.")
        return
    
    count = len(agents)
    confirm = input(f"You are about to delete {count} agents. Are you sure? (y/N): ")
    if confirm.lower() != 'y':
        print("Operation cancelled.")
        return
    
    for agent in agents:
        print(f"Deleting agent: {agent.display_name} (ID: {agent.name})")
        agent.delete()
        
    print(f"Successfully deleted {count} agents.")

def main():
    parser = argparse.ArgumentParser(description="Manage Vertex AI Agents")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List agents command
    list_parser = subparsers.add_parser("list", help="List all deployed agents")
    list_parser.add_argument("--filter", help="Filter agents by display name")
    
    # Get agent details command
    get_parser = subparsers.add_parser("get", help="Get details for a specific agent")
    get_parser.add_argument("resource_id", help="The resource ID or fully qualified name of the agent")
    
    # Delete specific agent command
    delete_parser = subparsers.add_parser("delete", help="Delete a specific agent")
    delete_parser.add_argument("resource_id", help="The resource ID or fully qualified name of the agent")
    
    # Delete all agents command
    delete_all_parser = subparsers.add_parser("delete-all", help="Delete all deployed agents")
    
    args = parser.parse_args()
    
    if args.command == "list":
        list_agents(args.filter)
    elif args.command == "get":
        get_agent_details(args.resource_id)
    elif args.command == "delete":
        delete_agent(args.resource_id)
    elif args.command == "delete-all":
        delete_all_agents()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()