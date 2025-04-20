package main

import (
	"fmt"
	"reflect"

	"github.com/Noooste/azuretls-client"
)

func main() {
	fmt.Println("Inspecting azuretls-client package")

	// Inspect Response struct
	resp := &azuretls.Response{}
	respType := reflect.TypeOf(*resp)
	fmt.Println("\nResponse struct fields:")
	for i := 0; i < respType.NumField(); i++ {
		field := respType.Field(i)
		fmt.Printf("%s: %s\n", field.Name, field.Type)
	}

	// Inspect Session struct
	session := azuretls.NewSession()
	sessionType := reflect.TypeOf(*session)
	fmt.Println("\nSession struct fields:")
	for i := 0; i < sessionType.NumField(); i++ {
		field := sessionType.Field(i)
		if !field.Anonymous {
			fmt.Printf("%s: %s\n", field.Name, field.Type)
		}
	}

	// Inspect OrderedHeaders
	fmt.Println("\nOrderedHeaders type:", reflect.TypeOf(azuretls.OrderedHeaders{}))
}
