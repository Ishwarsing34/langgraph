from langgraph.graph import StateGraph, START, END
from typing import TypedDict




#define state


class TemperatureState(TypedDict):
    temp_celsius: float
    temp_fahrenheit : float
    weather_status : str


def convert_temp(state:TemperatureState) -> TemperatureState:
    celsius = state['temp_celsius']
    #convert celsius to farenheit
    fahrenheit = (celsius * 9/5) + 32
    state['temp_fahrenheit'] = round(fahrenheit, 2)

    return state

#label weather condition

def label_weather(state: TemperatureState) -> TemperatureState:
    fahrenheit = state['temp_fahrenheit' ]
    if fahrenheit >= 86:
        state['weather_status' ] = 'Hot'
    elif fahrenheit >= 68:
        state['weather_status' ] = 'Warm'
    else:
        state['weather_status'] = 'Cold'

    return state


#define and compile graph


graph = StateGraph(TemperatureState)

#add the nodes to ur graph

graph.add_node('convert_temp', convert_temp)
graph.add_node('label_weather', label_weather)


#add edges to the graph


graph.add_edge(START, 'convert_temp')
graph.add_edge('convert_temp', 'label_weather')
graph.add_edge('label_weather',END)




#compile the graph


workflow = graph.compile()


#execute the graph


initial_state = {'temp_celsius':28.5}
final_state = workflow.invoke(initial_state)
print(final_state)

